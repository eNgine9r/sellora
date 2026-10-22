from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from scripts.recover_direct_historical_amounts import (
    candidate_numbers, evaluate_order, parse_seller_totals,
)


def sample(message, *, hours=-24, direction="OUTBOUND", date=None):
    when = (date or datetime(2026, 8, 21, 12, tzinfo=timezone.utc)) + timedelta(hours=hours)
    return SimpleNamespace(
        id=uuid4(),conversation_id=uuid4(),received_at=when,
        direction=direction,text=message,is_synthetic=False,
    )


def order_at():
    return SimpleNamespace(
        order_number="NP-20412345678901",
        created_at=datetime(2026, 8, 21, 12, tzinfo=timezone.utc),
    )


def match_source(buyer_response="Так, підходить", *, sibling_count=1):
    o=order_at()
    summary=sample("Товари: 679 грн і 340 грн, разом 1019 грн",hours=-36)
    confirmation=sample(buyer_response,hours=-33,direction="INBOUND")
    ttn=sample("Відправили ваш номер ТТН 20412345678901",hours=-4)
    msgs=[summary,confirmation,ttn]
    src,value,data=evaluate_order(o,summary.conversation_id,msgs,sibling_order_count=sibling_count)
    return src,value,data,summary,confirmation


def test_arithmetic_and_buyer_confirmation_give_high_confidence_without_revenue_mutation():
    src,val,evidence,m,buyer=match_source()
    assert src=="DIRECT_CONFIRMED_TOTAL"
    assert val==Decimal("1019")
    assert evidence["status"]=="AUTO_CONFIRMED"
    assert evidence["selected"]["message_id"]==str(m.id)
    assert evidence["selected"]["buyer_ack_message_id"]==str(buyer.id)
    assert evidence["selected"]["arithmetic_verified"]
    assert evidence["selected"]["matching_ttn_sent_later"]
    assert "Товари" not in str(evidence)  # never store raw chat content


def test_seller_total_and_ttn_without_buyer_affirmation_stays_estimate():
    src,val,evidence,*_=match_source("Коли буде відправка?")
    assert src=="DIRECT_ESTIMATED_TOTAL"
    assert val==Decimal("1019")
    assert evidence["status"]=="ESTIMATE"


def test_cancellation_blocks_auto_pricing():
    src,val,evidence,*_=match_source("Ні, не буду, скасуйте")
    assert src is None
    assert val is None
    assert evidence["status"]=="REVIEW_REQUIRED"


def test_overlapping_sales_in_same_thread_go_to_review():
    src,val,evidence,*_=match_source(sibling_count=2)
    assert src is None
    assert val is None
    assert evidence["conflicting_sibling_orders"]


def test_no_ttn_after_seller_total_does_not_auto_price():
    o=order_at()
    summary=sample("350 грн + 350 грн. Разом: 700 грн",hours=-12)
    src,val,evidence=evaluate_order(o,summary.conversation_id,[summary])
    assert src is None
    assert val is None
    assert evidence["status"]=="REVIEW_REQUIRED"


def test_correctly_count_duplicate_quoted_item_prices_in_arithmetic():
    summary=sample("Дві позиції: 350 грн і 350 грн, разом 700 грн")
    assert candidate_numbers(summary.text)==[350,350,700]
    assert parse_seller_totals(summary)[0]["arithmetic_verified"]


def test_delivery_cost_not_accidentally_summed_as_full_sale():
    summary=sample("Товар 679 грн, доставка 120 грн, разом 679 грн")
    parsed=parse_seller_totals(summary)
    assert parsed and not parsed[0]["arithmetic_verified"]


def test_non_purchase_prices_and_no_final_total_not_applied():
    o=order_at()
    m=sample("Товар коштує 749 грн. Доставка 120 грн.",hours=-24)
    src,value,evidence=evaluate_order(o,m.conversation_id,[m])
    assert src is None
    assert value is None
    assert evidence["status"]=="REVIEW_REQUIRED"


def test_synthetic_message_must_not_contribute():
    o=order_at()
    m=sample("Разом: 500 грн")
    m.is_synthetic=True
    src,value,evidence=evaluate_order(o,m.conversation_id,[m])
    assert value is None
    assert evidence["status"]=="NO_PRICE_MENTIONS"
