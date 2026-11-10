"""Backfill/live-link genuine inbound Instagram conversations to CRM Leads.

Creates only NEW leads, not orders, payments, revenue, customers or messages.
Uses the existing participant advisory lock and workspace isolation service.
"""
from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from sqlalchemy import func, select
from app.database.session import SessionLocal
from app.models.ai_direct import DirectConversation, DirectMessage
from app.models.workspace import Workspace
from app.services.direct_lead_service import DirectLeadService

LOOKBACK_DAYS = 14
CANDIDATE_LIMIT = 200
BATCH_LIMIT = 25
_ACK = {
    "дякую", "дякую вам", "спасибо", "спасибі", "thank you", "thanks",
    "ок", "окей", "okay", "ok", "добре", "зрозуміло", "клас", "супер",
    "👍", "🙏", "+", ".", "❤️",
}

def qualifies(text: str | None) -> bool:
    s = " ".join((text or "").casefold().split())
    if not s or s in _ACK:
        return False
    if s.startswith(("http://", "https://")) and len(s.split()) == 1:
        return False
    return sum(ch.isalpha() for ch in s) >= 2

def run_once(dry_run: bool = False):
    stats = {"candidates":0, "qualified":0, "linked":0, "failed":0, "dry_run":dry_run}
    with SessionLocal() as db:
        w=db.scalar(select(Workspace).where(Workspace.slug=="sellora",
                           Workspace.name=="Your Jewelry",Workspace.is_active.is_(True)))
        if not w:
            print("DIRECT_LEAD_WORKSPACE_MISSING")
            return 4
        start=datetime.now(UTC)-timedelta(days=LOOKBACK_DAYS)
        stmt=(select(DirectConversation.id)
            .join(DirectMessage,DirectMessage.conversation_id==DirectConversation.id)
            .where(
                DirectConversation.workspace_id==w.id,
                DirectConversation.linked_lead_id.is_(None),
                DirectConversation.linked_customer_id.is_(None),
                DirectMessage.workspace_id==w.id,
                DirectMessage.direction=="INBOUND",
                DirectMessage.provider=="INSTAGRAM",
                DirectMessage.is_synthetic.is_(False),
                DirectMessage.received_at>=start,
            )
            .group_by(DirectConversation.id)
            .order_by(func.max(DirectMessage.received_at).asc())
            .limit(CANDIDATE_LIMIT))
        ids=list(db.scalars(stmt).all())
        stats["candidates"]=len(ids)
        for cid in ids:
            msgs=list(db.scalars(
                select(DirectMessage)
                .where(DirectMessage.workspace_id==w.id,
                       DirectMessage.conversation_id==cid,
                       DirectMessage.direction=="INBOUND",
                       DirectMessage.provider=="INSTAGRAM",
                       DirectMessage.is_synthetic.is_(False),
                       DirectMessage.text.isnot(None))
                .order_by(DirectMessage.received_at.desc())
                .limit(10)
            ).all())
            chosen=next((m for m in msgs if qualifies(m.text)),None)
            if chosen is None:
                continue
            stats["qualified"]+=1
            if dry_run:
                continue
            if stats["linked"]>=BATCH_LIMIT:
                break
            try:
                service=DirectLeadService(db)
                # Participant+workspace locking and deduplication are performed by
                # the existing service; direct conversations stay authoritative.
                service._ensure(w.id,cid,actor_user_id=None,received_at=chosen.received_at)
                db.commit()
                stats["linked"]+=1
            except Exception as exc:
                db.rollback()
                stats["failed"]+=1
                print("DIRECT_LEAD_FAILED_SAFE",type(exc).__name__)
    print("DIRECT_LEAD_SYNC_SUMMARY"," ".join(f"{k}={v}" for k,v in stats.items()))
    return 0 if not stats["failed"] else 2

if __name__ == "__main__":
    raise SystemExit(run_once(dry_run=("--dry-run" in sys.argv)))
