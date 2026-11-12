"""Actual message evidence, never TTN or quoted price inferred as a sale."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.services.direct_sale_quote_service import (
    DirectSaleQuoteService, SaleQuoteContext, extract_quotes,
)
from app.services.smart_sale_confirmation_service import SmartSaleConfirmationService


BASE = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)
TTN_A = "20450000000001"
TTN_B = "20450000000002"


def message(text, *, days=0, direction="OUTBOUND", ident=None, synthetic=False):
    return SimpleNamespace(
        id=ident or uuid4(), text=text, received_at=BASE+timedelta(days=days),
        direction=direction, is_synthetic=synthetic, message_type="TEXT",
    )


def test_extract_unique_outbound_price_before_exact_ttn():
    quote=message("Вартість годинника 749 грн", days=-1)
    customer=message("Беру! 749 грн підходить", days=-0.5, direction="INBOUND")
    tracking=message("Ваша ТТН: "+TTN_A)
    result=extract_quotes([tracking, customer, quote], TTN_A)
    assert result.anchor_found
    assert [(p.amount,p.message_id) for p in result.prices] == [(Decimal("749"),quote.id)]
    assert quote.id in result.anchored_ids


def test_do_not_forge_price_from_inbound_or_bare_number():
    assert not extract_quotes([message(TTN_A),message("749 грн",direction="INBOUND")],TTN_A).prices
    assert not extract_quotes([message(TTN_A),message("749")],TTN_A).prices


def test_multiple_distinct_quotes_require_price_choice_not_one_guess():
    a=message("Браслет 679 грн", days=-2)
    b=message("Годинник 749 грн", days=-1)
    ctx=extract_quotes([message("ТТН "+TTN_A), a, b], TTN_A)
    assert [p.amount for p in ctx.prices]==[Decimal("749"),Decimal("679")]


def test_repeated_price_quotes_dedup():
    first=message("749 грн",days=-2)
    last=message("₴749",days=-1)
    ctx=extract_quotes([message(TTN_A),first,last],TTN_A)
    assert len(ctx.prices)==1
    assert ctx.prices[0].message_id==last.id


def test_preceding_external_ttn_is_strict_sales_boundary():
    previous=message("Надіслано "+TTN_B,days=-3)
    older=message("Браслет 679 грн",days=-4)
    current=message("Годинник 749 грн",days=-1)
    ctx=extract_quotes([older,previous,current,message(TTN_A)],TTN_A)
    assert [p.amount for p in ctx.prices]==[Decimal("749")]
    assert older.id not in ctx.anchored_ids


def test_outbound_prices_after_ttn_or_older_than_week_are_ignored():
    ctx=extract_quotes([message(TTN_A),message("679 грн",days=1),message("749 грн",days=-8)],TTN_A)
    assert ctx.anchor_found and not ctx.prices


def test_delivery_iban_ttn_and_numerical_noise_do_not_become_prices():
    ctx=extract_quotes([
        message(TTN_A),
        message("Доставка 150 грн",days=-1),
        message("Передплата 500 грн",days=-1.5),
        message("20450000000000",days=-2),
        message("Номер картки 4444222233331111",days=-2.5),
        message("Ціна 749 грн, а інший варіант 679 грн",days=-3),
    ],TTN_A)
    assert ctx.prices==()


def test_multiple_exact_tracking_mentions_need_human_review():
    ctx=extract_quotes([message(TTN_A),message("ТТН "+TTN_A,days=-1),message("749 грн",days=-2)],TTN_A)
    assert not ctx.anchor_found and not ctx.prices and not ctx.anchored_ids


def test_synthetic_ttn_cannot_anchor_real_sale():
    ctx=extract_quotes([message(TTN_A,synthetic=True),message("749 грн",days=-1)],TTN_A)
    assert not ctx.anchor_found and not ctx.prices


def test_bounded_price_count_and_comma():
    amounts=[message(f"Ціна {300+i} грн",days=-(i+1)/10) for i in range(7)]
    ctx=extract_quotes([message(TTN_A), *amounts, message("Ціна 749,50 грн",days=-0.03)],TTN_A)
    assert len(ctx.prices)==4
    assert ctx.prices[0].amount==Decimal("749.50")


def test_malformed_tracking_number_yields_no_evidence():
    assert not extract_quotes([message(TTN_A)],"4444222233331111").anchor_found


def test_exact_sku_from_old_sale_cannot_prefill_new_ttn():
    vid=uuid4()
    old_message=uuid4()
    candidate=SimpleNamespace(
        variant_id=vid, sku="WATCH-001", product_name="Watch",
        price=Decimal("749.00"), available_quantity=7,
    )
    line=SimpleNamespace(source="INBOUND_SKU", match_status="MATCHED",
        requires_review=False,candidates=[candidate],quantity=1,
        evidence=[SimpleNamespace(message_id=old_message)],candidates_truncated=False)
    svc=SmartSaleConfirmationService.__new__(SmartSaleConfirmationService)
    svc.proposals=SimpleNamespace(get=lambda w,c:SimpleNamespace(
        catalog_truncated=False,context_truncated=False,lines=[line],
    ))
    context=SaleQuoteContext(frozenset(),(),True)
    assert svc._suggestion(uuid4(),uuid4(),context) is None
    context=SaleQuoteContext(frozenset([old_message]),(),True)
    assert svc._suggestion(uuid4(),uuid4(),context).variant_id==vid
    assert svc._suggestion(uuid4(),uuid4(),SaleQuoteContext(frozenset([old_message]),(),False)) is None


def test_get_scopes_workspace_and_conversation_and_bounds_history():
    class FakeDb:
        def __init__(self):
            self.statement=None
        def scalars(self,s):
            self.statement=s
            return SimpleNamespace(all=lambda:[])
    db=FakeDb()
    w,c=uuid4(),uuid4()
    service=DirectSaleQuoteService(db)
    assert not service.get(w,c,TTN_A).anchor_found
    query=db.statement.compile(dialect=postgresql.dialect())
    sql=str(query)
    assert "direct_messages.workspace_id" in sql
    assert "direct_messages.conversation_id" in sql
    assert w in query.params.values() and c in query.params.values()
    assert "LIMIT" in sql
