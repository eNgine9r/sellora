"""Fill separately labelled, non-revenue historical order amounts.

Order.revenue/net_profit and order item prices are deliberately untouched.
Defaults to dry-run. Use --execute only after migration 041 and fresh backup.
"""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation

from sqlalchemy import select, text

from app.database.session import SessionLocal
from app.models.order import Order
from app.models.shipment import Shipment
from app.models.workspace import Workspace
from app.repositories.audit_log_repository import AuditLogRepository
from app.services.nova_poshta_service import NovaPoshtaSettingsService
from app.integrations.nova_poshta_client import NovaPoshtaClient
from scripts.reconcile_nova_archive import retrieve_complete_month

SOURCE_COD = "NP_COD_REQUESTED"
SOURCE_DECLARED = "NP_DECLARED_VALUE"


def amount(raw):
    try:
        value = Decimal(str(raw).strip())
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not value.is_finite() or value <= 0 or value > Decimal("999999.99"):
        return None
    return value.quantize(Decimal("0.01"))


def select_candidates(db, workspace_id, month=None, client=None):
    orders = db.scalars(select(Order).where(
        Order.workspace_id == workspace_id,
        Order.deleted_at.is_(None), Order.order_number.like("NP-%"),
        Order.is_historical.is_(True),
    )).all()
    order_map={order.order_number[3:]:order for order in orders}
    shipments=db.scalars(select(Shipment).where(
        Shipment.workspace_id==workspace_id,Shipment.deleted_at.is_(None),
        Shipment.carrier=="NOVA_POSHTA",
    )).all()
    shipments_by_tracking={}
    for shipment in shipments:
        if not shipment.tracking_number or shipment.tracking_number not in order_map:
            continue
        if shipment.tracking_number in shipments_by_tracking:
            raise RuntimeError("STOP_DUPLICATE_SHIPMENT")
        if shipment.order_id != order_map[shipment.tracking_number].id:
            raise RuntimeError("STOP_SHIPMENT_ORDER_ID_MISMATCH")
        shipments_by_tracking[shipment.tracking_number]=shipment
    candidates={}
    counters=Counter()
    # COD requested amount is a quoted collection amount, not a completed sale.
    for ttn, shipment in shipments_by_tracking.items():
        value=amount(shipment.cod_amount)
        if value is not None:
            candidates[ttn]=(value,SOURCE_COD)
            counters["cod_evidence"]+=1
    if month:
        if client is None:
            raise RuntimeError("STOP_PROVIDER_CLIENT_REQUIRED")
        year,monthnum=map(int,month.split("-"))
        if year != 2026 or not 5 <= monthnum <= 10:
            raise RuntimeError("STOP_OUT_OF_SCOPE_PROVIDER_MONTH")
        docs=retrieve_complete_month(client,year,monthnum)
        counters["provider_documents"]=len(docs)
        for ttn,doc in docs.items():
            if ttn not in order_map or ttn not in shipments_by_tracking:
                continue
            if ttn in candidates:
                continue
            # Cost = declared/insured parcel value; NEVER assume recognized revenue.
            declared=amount(doc.get("Cost"))
            if declared is None:
                counters["no_declared_value"]+=1
                continue
            candidates[ttn]=(declared,SOURCE_DECLARED)
            counters["declared_estimate_evidence"]+=1
    counters["candidate_rows"]=len(candidates)
    return order_map,candidates,counters


def fill(db, workspace_id, order_map, candidates, *, dry_run):
    counters=Counter()
    totals=Counter()
    audit=AuditLogRepository(db) if not dry_run else None
    for ttn,(value,source) in sorted(candidates.items()):
        order=order_map[ttn]
        if order.historical_order_value is not None:
            if order.historical_order_value != value or order.historical_value_source != source:
                counters["existing_conflict"]+=1
            else:
                counters["already_populated"]+=1
            continue
        if order.revenue != 0 or order.net_profit != 0 or not order.is_historical:
            counters["invalid_existing_financial_context"]+=1
            continue
        if not dry_run:
            order.historical_order_value=value
            order.historical_value_source=source
            audit.create(workspace_id=workspace_id,user_id=None,
                         entity_type="Order",entity_id=order.id,
                         action="NP_HISTORICAL_AMOUNT_ESTIMATED",
                         new_value={"source":source,"estimated_amount":str(value),
                                    "not_confirmed_revenue":True})
        counters["new_"+source]+=1
        totals[source]+=value
    return counters,totals


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--month",choices=[f"2026-{i:02}" for i in range(5,11)])
    args=parser.parse_args()
    with SessionLocal() as db:
        if not args.execute:
            db.execute(text("SET TRANSACTION READ ONLY"))
        workspace=db.scalar(select(Workspace.id).where(
            Workspace.name.ilike("%Your Jewelry%")).limit(1))
        assert workspace is not None,"NO_EXISTING_WORKSPACE"
        client=None
        if args.month:
            connection,key=NovaPoshtaSettingsService(db)._require_connection(workspace)
            assert connection.status=="CONNECTED"
            client=NovaPoshtaClient(key,timeout_seconds=20)
        orders,candidates,selection=select_candidates(db,workspace,args.month,client)
        changes,totals=fill(db,workspace,orders,candidates,dry_run=not args.execute)
        print("AMOUNT_BACKFILL",args.month or "COD_FROM_LOCAL_SHIPMENTS",
              "MODE","EXECUTE" if args.execute else "DRY_RUN",
              "SOURCE_COUNTS",dict(selection),"CHANGES",dict(changes),
              "NEW_AMOUNT_TOTALS",{k:str(v) for k,v in totals.items()},flush=True)
        if args.execute:
            if changes["existing_conflict"] or changes["invalid_existing_financial_context"]:
                raise RuntimeError("STOP_BACKFILL_INTEGRITY_CONFLICT")
            db.commit()
            print("AMOUNT_BACKFILL_COMMITTED",sum(v for k,v in changes.items() if k.startswith("new_")),flush=True)
        else:
            db.rollback()
            print("NO_DATABASE_CHANGES",flush=True)


if __name__=="__main__":
    main()
