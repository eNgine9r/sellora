"""Evidence-driven Instagram Direct historical order value attribution.

CLI-only one-time maintenance. --execute requires schema 202610220042 and a verified
backup. Never treats message text as proof of payment or booked revenue.
"""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text

from app.database.session import SessionLocal
from app.models.workspace import Workspace
from app.models.order import Order
from app.models.customer import Customer
from app.models.ai_direct import DirectMessage
from app.repositories.audit_log_repository import AuditLogRepository

VERSION="direct-total-v1"
MONEY=re.compile(r"(?<![\d\w])([1-9]\d{2,4})(?:[\s.,](?:00))?\s*(?:грн\.?|₴|uah|грив(?:ень|ні)?)(?!\w)",re.I)
TOTAL=re.compile(r"(?:разом|всього|загалом|итого|до\s*оплат[ии]|за\s*все)\s*[:=\-]?\s*([1-9]\d{2,4})(?:[\s.,](?:00))?\s*(?:грн\.?|₴|uah)?",re.I)
ACCEPT=re.compile(r"(?:^|\W)(?:так|добре|ок|окей|оформл(?:юйте|яйте|ямо|іть)|беру|підтвердж(?:ую|уємо)|підходить|все\s*вірно|все\s*правильно|відправляйте|давайте)(?:\W|$)",re.I)
CANCEL=re.compile(r"(?:не\s+(?:потрібно|беру|буду|відправляйте)|відмін[аи]|скасу|поверненн|обмін|не\s+буду|передумал|не\s+підход)",re.I)

def candidate_numbers(content: str) -> list[int]:
    """Keep duplicates so 350+350=700 can be checked accurately."""
    return [int(x) for x in MONEY.findall(content) if 100<=int(x)<=50000]

def parse_seller_totals(message: DirectMessage) -> list[dict[str, Any]]:
    if message.direction != "OUTBOUND" or not message.text or message.is_synthetic:
        return []
    prices=candidate_numbers(message.text)
    parsed=[]
    for raw in TOTAL.findall(message.text):
        total=int(raw)
        if not 100<=total<=50000:
            continue
        # Candidate must be written with UAH, or be followed by a currency
        # qualifier in a close context. Avoid invoice/order/phone integers.
        if total not in prices:
            continue
        other=list(prices)
        other.remove(total)
        arith=bool(other) and sum(other)==total
        parsed.append({
            "message_id": str(message.id),
            "conversation_id": str(message.conversation_id),
            "amount":total,
            "arithmetic_verified":arith,
            "source_message_at":message.received_at.isoformat(),
        })
    return parsed

def evaluate_order(order, conversation_id, messages, *, sibling_order_count=1):
    window=sorted(
        (m for m in messages if m.received_at and -120<=
         (m.received_at-order.created_at).total_seconds()/3600<=48),
        key=lambda m:m.received_at
    )
    summaries=[]
    prices=[]
    for m in window:
        if m.is_synthetic or not m.text:
            continue
        values=candidate_numbers(m.text)
        if values:
            prices.append((m,values))
        summaries.extend((m,c) for c in parse_seller_totals(m))
    possible=[]
    for m,c in summaries:
        later=[x for x in window if x.received_at>m.received_at and
               x.received_at<=m.received_at+timedelta(days=3)]
        buyers=[x for x in later if x.direction=="INBOUND" and x.text]
        accepted=any(ACCEPT.search(x.text) and not CANCEL.search(x.text) for x in buyers)
        cancelled=any(CANCEL.search(x.text or "") for x in buyers)
        sent_ttn=any(
            order.order_number[3:] in (x.text or "") and x.direction=="OUTBOUND"
            for x in later
        )
        possible.append({
            **c,
            "buyer_acknowledged":bool(accepted),
            "cancellation_language":bool(cancelled),
            "matching_ttn_sent_later":bool(sent_ttn),
            "buyer_ack_message_id":next(
                (str(x.id) for x in buyers if ACCEPT.search(x.text or "")
                 and not CANCEL.search(x.text or "")),None
            ),
        })
    distinct_totals={x["amount"] for x in possible}
    blocked=sibling_order_count>1
    approved=None
    if len(possible)==1 and len(distinct_totals)==1:
        c=possible[0]
        if c["arithmetic_verified"] and c["matching_ttn_sent_later"] and not c["cancellation_language"] and not blocked:
            approved=c
    if approved:
        source="DIRECT_CONFIRMED_TOTAL" if approved["buyer_acknowledged"] else "DIRECT_ESTIMATED_TOTAL"
        status="AUTO_CONFIRMED" if approved["buyer_acknowledged"] else "ESTIMATE"
    elif possible:
        source=None; status="REVIEW_REQUIRED"
    elif prices:
        source=None;status="REVIEW_REQUIRED"
    else:
        source=None;status="NO_PRICE_MENTIONS"
    ranked=[
        {
            "message_id":str(m.id),
            "conversation_id":str(m.conversation_id),
            "values":[str(v) for v in sorted(set(values))],
            "seller":m.direction=="OUTBOUND",
            "source_message_at":m.received_at.isoformat(),
            "explicit_total":any(str(m.id)==entry["message_id"] for entry in possible),
        }
        for m,values in sorted(
            prices,key=lambda item:(abs((item[0].received_at-order.created_at).total_seconds()),
                                    item[0].received_at)
        )[:50]
    ]
    evidence={
        "analysis_version":VERSION,
        "status":status,
        "selected":approved,
        "total_candidates":possible,
        "total_price_messages":len(prices),
        "review_candidates":ranked,
        "review_truncated":max(len(prices)-len(ranked),0),
        "conflicting_sibling_orders":blocked,
    }
    return source,Decimal(approved["amount"]) if approved else None,evidence

def load_inputs(db,workspace_id):
    orders=db.scalars(select(Order).where(
        Order.workspace_id==workspace_id,
        Order.order_number.like("NP-%"),
        Order.deleted_at.is_(None),Order.is_historical.is_(True),
        Order.historical_order_value.is_(None)
    )).all()
    people={c.id:c for c in db.scalars(select(Customer).where(
        Customer.workspace_id==workspace_id,Customer.deleted_at.is_(None)
    ))}
    cid_to_orders=defaultdict(list)
    for order in orders:
        customer=people.get(order.customer_id)
        if not customer or not customer.source_direct_conversation_id:
            continue
        cid_to_orders[customer.source_direct_conversation_id].append(order)
    messages=defaultdict(list)
    if cid_to_orders:
        for m in db.scalars(select(DirectMessage).where(
            DirectMessage.workspace_id==workspace_id,
            DirectMessage.conversation_id.in_(list(cid_to_orders)),
            DirectMessage.deleted_at.is_(None),
        )):
            messages[m.conversation_id].append(m)
    return orders,people,cid_to_orders,messages

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--execute",action="store_true")
    args=parser.parse_args()
    with SessionLocal() as db:
        if not args.execute:db.execute(text("SET TRANSACTION READ ONLY"))
        ws=db.scalar(select(Workspace.id).where(Workspace.name.ilike("%Your Jewelry%")).limit(1))
        assert ws is not None
        orders,people,conversations,messages=load_inputs(db,ws)
        audit=AuditLogRepository(db) if args.execute else None
        changes=Counter();total=Counter()
        for order in orders:
            customer=people.get(order.customer_id)
            cid=customer.source_direct_conversation_id if customer else None
            if cid is None:
                changes["no_linked_conversation"]+=1
                continue
            siblings=sum(
                abs((other.created_at-order.created_at).total_seconds())<=86400*5
                for other in conversations[cid]
            )
            source,value,evidence=evaluate_order(
                order,cid,messages[cid],sibling_order_count=siblings
            )
            changes["status_"+evidence["status"]]+=1
            if value is not None:
                if order.revenue!=0 or order.net_profit!=0 or order.payment_status!="PENDING":
                    raise RuntimeError("STOP_ACCOUNTING_CONTEXT_CHANGED")
                changes["new_"+source]+=1
                total[source]+=value
            if args.execute:
                # No plain message text/phone/customer data copied into DB evidence.
                order.historical_value_evidence=evidence
                if value is not None:
                    order.historical_order_value=value
                    order.historical_value_source=source
                    audit.create(
                        workspace_id=ws,user_id=None,entity_type="Order",entity_id=order.id,
                        action="DIRECT_HISTORICAL_AMOUNT_RECONCILED",
                        new_value={
                            "source":source,
                            "amount":str(value),
                            "message_id":evidence["selected"]["message_id"],
                            "conversation_id":evidence["selected"]["conversation_id"],
                            "buyer_ack_message_id":evidence["selected"]["buyer_ack_message_id"],
                            "arith_verified":True,
                            "ttn_verified":True,
                            "not_realized_revenue":True,
                        },
                    )
        print("DIRECT_PRICE_RECONCILE",
              "MODE","EXECUTE" if args.execute else "DRY_RUN",
              "SCANNED",len(orders),
              "STATUS_COUNTS",dict(changes),
              "AMOUNTS",{k:str(v) for k,v in total.items()},flush=True)
        if args.execute:
            db.flush()
            db.commit()
            print("DIRECT_PRICE_EVIDENCE_SAVED",len(orders),flush=True)
        else:
            db.rollback()
            print("NO_DATABASE_MUTATIONS",flush=True)

if __name__=="__main__":
    main()
