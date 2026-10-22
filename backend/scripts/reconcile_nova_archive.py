"""Conservative, idempotent reconstruction of NP/Instagram historical orders.

Execute one complete provider month at a time. No fuzzy name/price matching.
Never treat provider document creation as delivery or payment confirmation.
"""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from zoneinfo import ZoneInfo
from decimal import Decimal, InvalidOperation

from sqlalchemy import select, text

from app.database.session import SessionLocal
from app.models.workspace import Workspace
from app.models.ai_direct import DirectConversation, DirectMessage
from app.models.customer import Customer
from app.models.customer_address import CustomerAddress
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.shipment import Shipment
from app.repositories.audit_log_repository import AuditLogRepository
from app.services.nova_poshta_service import NovaPoshtaSettingsService
from app.integrations.nova_poshta_client import NovaPoshtaClient
from app.utils.phone import normalize_ua_phone, PhoneNormalizationError

TTN_RE = re.compile(r"(?<!\d)(?:20|59)\d{12}(?!\d)")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?38[ \t()\-]*)?0(?:[ \t()\-]*\d){9}(?!\d)")
ARCHIVE_SKU = "NP-ARCHIVE-OTHER"


def normalize_phone(raw):
    try:
        return normalize_ua_phone(str(raw)) if raw else None
    except PhoneNormalizationError:
        return None


def retrieve_complete_month(client, year, month):
    import calendar
    last = calendar.monthrange(year, month)[1]
    if (year, month) == (2026, 10):
        last = 22
    params = {
        "DateTimeFrom": f"01.{month:02}.{year}",
        "DateTimeTo": f"{last:02}.{month:02}.{year}",
        "GetFullList": "1",
    }
    collected = {}
    total = None
    for page in range(1, 31):
        payload = client._call("InternetDocument", "getDocumentList", {**params, "Page": str(page)})
        records = payload.get("data") or []
        total = int((payload.get("info") or {}).get("totalCount") or 0)
        for item in records:
            number = str(item.get("IntDocNumber") or "").strip()
            if number:
                if number in collected and collected[number] != item:
                    raise RuntimeError("STOP_CONFLICTING_WAYBILL_DUPLICATE")
                collected[number] = item
        if len(collected) >= total:
            break
        if len(records) < 100:
            raise RuntimeError("STOP_ARCHIVE_PAGINATION_INCOMPLETE")
    if total is None or len(collected) != total:
        raise RuntimeError("STOP_ARCHIVE_TOTAL_COUNT_MISMATCH")
    return collected


def strong_candidates(db, workspace, documents):
    ttn_conversations = defaultdict(set)
    phone_conversations = defaultdict(set)
    conversations = {
        x.id: x for x in db.scalars(
            select(DirectConversation).where(
                DirectConversation.workspace_id == workspace,
                DirectConversation.channel == "INSTAGRAM",
                DirectConversation.deleted_at.is_(None),
            )
        )
    }
    for cid, body, direction in db.execute(
        select(DirectMessage.conversation_id, DirectMessage.text, DirectMessage.direction).where(
            DirectMessage.workspace_id == workspace,
            DirectMessage.deleted_at.is_(None),
            DirectMessage.text.is_not(None),
        )
    ):
        if cid not in conversations:
            continue
        for number in set(TTN_RE.findall(body or "")):
            ttn_conversations[number].add(cid)
        if direction == "INBOUND":
            for raw in set(PHONE_RE.findall(body or "")):
                normalized = normalize_phone(raw)
                if normalized:
                    phone_conversations[normalized].add(cid)

    selected = {}
    counts = Counter()
    names_by_phone = defaultdict(set)
    threads_by_phone = defaultdict(set)
    for number, doc in documents.items():
        counts["documents"] += 1
        phone = normalize_phone(doc.get("RecipientsPhone") or doc.get("RecipientContactPhone"))
        name = " ".join(str(doc.get("RecipientContactPerson") or doc.get("RecipientDescription") or "").split())
        city = " ".join(str(doc.get("CityRecipientDescription") or "").split())
        warehouse = " ".join(str(doc.get("RecipientAddressDescription") or "").split())
        by_ttn = ttn_conversations.get(number, set())
        by_phone = phone_conversations.get(phone, set()) if phone else set()
        if len(by_ttn) != 1:
            counts["missing_or_ambiguous_direct_ttn"] += 1
            continue
        if by_ttn != by_phone:
            counts["missing_or_conflicting_inbound_phone"] += 1
            continue
        if not all((phone, name, city, warehouse)):
            counts["missing_recipient_details"] += 1
            continue
        cid = next(iter(by_ttn))
        selected[number] = (doc, cid, phone, name, city, warehouse)
        names_by_phone[phone].add(name.casefold())
        threads_by_phone[phone].add(cid)
    # A repeated label for the same recipient and parcel details is not proof
    # of a second sale. Route all indistinguishable siblings to review.
    by_fingerprint = defaultdict(set)
    for number, (doc, cid, phone, name, city, warehouse) in selected.items():
        by_fingerprint[(phone, str(doc.get("DateTime") or "")[:10],
                        warehouse.casefold(), str(doc.get("AfterpaymentOnGoodsCost") or "0"))].add(number)
    filtered = {}
    for number, row in selected.items():
        doc, cid, phone, name, city, warehouse = row
        fingerprint=(phone, str(doc.get("DateTime") or "")[:10],
                     warehouse.casefold(), str(doc.get("AfterpaymentOnGoodsCost") or "0"))
        if len(by_fingerprint[fingerprint]) > 1:
            counts["possible_duplicate_waybill_same_day"] += 1
        elif len(names_by_phone[phone]) > 1 or len(threads_by_phone[phone]) > 1:
            counts["conflicting_recipient_identity"] += 1
        else:
            filtered[number] = row
    counts["strong_candidates"] = len(filtered)
    return filtered, conversations, counts


def reconstruct(db, workspace, rows, conversations, counters):
    customers = list(db.scalars(select(Customer).where(
        Customer.workspace_id == workspace, Customer.deleted_at.is_(None)
    )))
    by_phone = defaultdict(set)
    for c in customers:
        p = normalize_phone(c.phone)
        if p:
            by_phone[p].add(c.id)
    customer_ids = {c.id: c for c in customers}
    shipments = {
        s.tracking_number for s in db.scalars(select(Shipment).where(
            Shipment.workspace_id == workspace, Shipment.deleted_at.is_(None)
        )) if s.tracking_number
    }
    existing_orders = {
        o.order_number for o in db.scalars(select(Order).where(
            Order.workspace_id == workspace, Order.deleted_at.is_(None)
        ))
    }
    addresses = defaultdict(set)
    for adr in db.scalars(select(CustomerAddress).where(
        CustomerAddress.workspace_id == workspace, CustomerAddress.deleted_at.is_(None)
    )):
        addresses[adr.customer_id].add((
            (adr.city or "").casefold(), (adr.address_line1 or "").casefold()
        ))
    processed_phone = {}
    seen_orders = set()
    pending = []
    for number, (doc, cid, phone, name, city, warehouse) in sorted(rows.items()):
        order_number = "NP-" + number
        if number in shipments or order_number in existing_orders:
            counters["already_imported_ttn"] += 1
            continue
        conv = conversations[cid]
        matches = by_phone.get(phone, set())
        if len(matches) > 1:
            counters["ambiguous_existing_phone"] += 1
            continue
        customer = customer_ids[next(iter(matches))] if matches else None
        if customer and (
            customer.instagram_scoped_id and conv.participant_scoped_id
            and customer.instagram_scoped_id != conv.participant_scoped_id
        ):
            counters["conflicting_existing_instagram_identity"] += 1
            continue
        if customer and " ".join(customer.name.split()).casefold() != name.casefold():
            counters["conflicting_existing_recipient_name"] += 1
            continue
        if customer and customer.source_direct_conversation_id not in (None, cid):
            counters["conflicting_existing_conversation"] += 1
            continue
        if conv.linked_customer_id and (not customer or conv.linked_customer_id != customer.id):
            counters["conflicting_linked_customer"] += 1
            continue
        if phone in processed_phone and processed_phone[phone] != cid:
            counters["conflicting_customer_phone"] += 1
            continue
        try:
            original_date = datetime.fromisoformat(str(doc.get("DateTime") or ""))
            if original_date.tzinfo is None:
                original_date = original_date.replace(tzinfo=ZoneInfo("Europe/Kyiv"))
            original_date = original_date.astimezone(UTC)
        except ValueError:
            counters["invalid_waybill_date"] += 1
            continue
        if original_date.year != 2026 or original_date.month < 5:
            counters["overlaps_existing_financial_history"] += 1
            continue
        pending.append((number, doc, cid, phone, name, city, warehouse, customer, original_date))
        processed_phone[phone] = cid

    if not pending:
        return 0
    # One generic product only, no inventory transactions or fabricated SKU match.
    variant = db.scalar(select(ProductVariant).where(
        ProductVariant.workspace_id == workspace, ProductVariant.sku == ARCHIVE_SKU,
        ProductVariant.deleted_at.is_(None)
    ).limit(1))
    audit = AuditLogRepository(db)
    if variant is None:
        product = Product(
            workspace_id=workspace,
            name="Інше (товар з історичної ТТН не визначено)",
            sku=ARCHIVE_SKU, category="Інше", is_active=False,
        )
        db.add(product)
        db.flush()
        variant = ProductVariant(
            workspace_id=workspace, product_id=product.id, sku=ARCHIVE_SKU, price=Decimal("0.00"), is_active=False
        )
        db.add(variant)
        db.flush()
        audit.create(workspace_id=workspace,user_id=None,entity_type="Product",entity_id=product.id,
                     action="NOVA_HISTORY_UNKNOWN_PRODUCT",new_value={"sku":ARCHIVE_SKU})

    for number, doc, cid, phone, name, city, warehouse, previous_customer, dt in pending:
        conv = conversations[cid]
        current_ids = by_phone.get(phone, set())
        customer = customer_ids[next(iter(current_ids))] if current_ids else previous_customer
        if customer is None:
            customer = Customer(
                workspace_id=workspace, name=name, phone=phone,
                instagram_scoped_id=conv.participant_scoped_id,
                instagram_username=conv.participant_username,
                source_direct_conversation_id=cid,
                source="INSTAGRAM_DIRECT", lifecycle_status="CUSTOMER",
                profile_status="INCOMPLETE", city=city,
            )
            db.add(customer)
            db.flush()
            by_phone[phone].add(customer.id)
            customer_ids[customer.id] = customer
            counters["created_customers"] += 1
            audit.create(workspace_id=workspace,user_id=None,entity_type="Customer",entity_id=customer.id,
                         action="NOVA_DIRECT_CUSTOMER_RECONCILED",new_value={"method":"TTN+INBOUND_PHONE"})
        elif not customer.source_direct_conversation_id:
            customer.source_direct_conversation_id = cid
            if not customer.instagram_scoped_id:
                customer.instagram_scoped_id = conv.participant_scoped_id
            if not customer.city:
                customer.city = city
            counters["enriched_existing_customers"] += 1
        if not conv.linked_customer_id:
            conv.linked_customer_id = customer.id
            counters["linked_direct_conversations"] += 1
        key = (city.casefold(), warehouse.casefold())
        if key not in addresses[customer.id]:
            adr = CustomerAddress(
                workspace_id=workspace, customer_id=customer.id,
                label="Нова пошта (архів)", recipient_name=name, phone=phone,
                address_line1=warehouse, city=city, country="Україна",
                is_default=not addresses[customer.id],
                delivery_provider="NOVA_POSHTA",
                nova_poshta_city_ref=str(doc.get("RecipientCityRef") or "") or None,
                nova_poshta_warehouse_ref=str(doc.get("RecipientWarehouseRef") or "") or None,
            )
            db.add(adr)
            addresses[customer.id].add(key)
            counters["created_delivery_addresses"] += 1
        order = Order(
            workspace_id=workspace, order_number="NP-" + number,
            customer_id=customer.id, status="CONFIRMED",
            payment_status="PENDING", is_historical=True,
            revenue=Decimal("0.00"), product_cost=Decimal("0.00"),
            ad_cost=Decimal("0.00"), shipping_cost=Decimal("0.00"), cod_fee=Decimal("0.00"),
            other_cost=Decimal("0.00"), net_profit=Decimal("0.00"),
            notes="Історична ТТН з Direct: номер і телефон підтверджені. "
                  "Товар, факт оплати та вручення не встановлені. "
                  "Дохід і витрати не враховано.",
            created_at=dt,
        )
        db.add(order)
        db.flush()
        db.add(OrderItem(
            workspace_id=workspace, order_id=order.id, product_variant_id=variant.id,
            sku=ARCHIVE_SKU, product_name="Інше (товар не визначено)",
            quantity=1, unit_price=Decimal("0.00"), unit_cost=Decimal("0.00"),
            line_total=Decimal("0.00"), line_cost=Decimal("0.00"),
        ))
        cod = Decimal("0.00")
        try:
            cod = max(Decimal("0"), Decimal(str(doc.get("AfterpaymentOnGoodsCost") or "0")))
        except InvalidOperation:
            pass
        db.add(Shipment(
            workspace_id=workspace, order_id=order.id, customer_id=customer.id,
            tracking_number=number, carrier="NOVA_POSHTA", status="CREATED",
            recipient_name=name, recipient_phone=phone, city=city, warehouse=warehouse,
            cod_amount=cod, external_provider="NOVA_POSHTA",
            external_ref=str(doc.get("Ref") or "") or None,
            nova_poshta_document_ref=str(doc.get("Ref") or "") or None,
            nova_poshta_document_number=number,
            nova_poshta_city_ref=str(doc.get("RecipientCityRef") or "") or None,
            nova_poshta_warehouse_ref=str(doc.get("RecipientWarehouseRef") or "") or None,
            nova_poshta_raw_status=str(doc.get("StateName") or "")[:255] or None,
        ))
        audit.create(workspace_id=workspace,user_id=None,entity_type="Order",entity_id=order.id,
                     action="NOVA_DIRECT_HISTORICAL_ORDER_RECONCILED",
                     new_value={"method":"TTN+INBOUND_PHONE","financial_values_unknown":True,"product":"OTHER"})
        audit.create(workspace_id=workspace,user_id=None,entity_type="Shipment",entity_id=order.id,
                     action="NOVA_DIRECT_SHIPMENT_HISTORY_IMPORTED",
                     new_value={"provider":"NOVA_POSHTA","status":"CREATED","delivery_unverified":True})
        counters["created_historical_orders"] += 1
        counters["created_np_shipments"] += 1
        seen_orders.add(number)
    return len(seen_orders)


def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--month", required=True, choices=[f"2026-{n:02d}" for n in range(5,11)])
    cli.add_argument("--execute", action="store_true")
    args=cli.parse_args()
    year, month=map(int,args.month.split("-"))
    with SessionLocal() as db:
        db.execute(text("SET TRANSACTION READ ONLY")) if not args.execute else None
        workspace=db.scalar(select(Workspace.id).where(
            Workspace.name.ilike("%Your Jewelry%")
        ).limit(1))
        assert workspace
        connection, key=NovaPoshtaSettingsService(db)._require_connection(workspace)
        assert connection.status == "CONNECTED"
        documents=retrieve_complete_month(NovaPoshtaClient(key,timeout_seconds=18),year,month)
        rows,conversations,counts=strong_candidates(db,workspace,documents)
        if not args.execute:
            print("NOVA_RECONCILE",args.month,"MODE","READ_ONLY_PREVIEW",
                  "RESULTS",dict(counts),flush=True)
            db.rollback()
            print("NO_DATABASE_CHANGES",flush=True)
            return
        reconstructed=reconstruct(db,workspace,rows,conversations,counts)
        print("NOVA_RECONCILE",args.month,"MODE","EXECUTE",
              "RESULTS",dict(counts),"ORDERS_READY",reconstructed,flush=True)
        db.commit()
        print("TRANSACTION_COMMITTED",reconstructed,flush=True)


if __name__=="__main__":
    main()
