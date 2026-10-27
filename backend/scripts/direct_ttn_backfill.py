"""Operator-only, evidence-gated historical Direct→Shipment→Order backfill.

Defaults to an aggregate-only, read-only preview. No customer data is logged.
Never deploy/run --apply before schema-046, live-code parity and a backup are
verified. An explicit owner-approved maintenance run must pass two counters,
an actor UUID and a deployment-only allow flag; otherwise it cannot write.
"""
from __future__ import annotations

import argparse
import os
from uuid import UUID

from sqlalchemy import select, text

from app.database.session import SessionLocal
from app.models.ai_direct import DirectConversation
from app.services.direct_ttn_evidence_service import DirectTtnEvidenceService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-id", type=UUID, required=True)
    parser.add_argument("--apply", action="store_true", help="Write only reviewed exact-TTN relationships")
    parser.add_argument("--expected-conversations", type=int)
    parser.add_argument("--expected-links", type=int)
    parser.add_argument("--actor-id", type=UUID)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.apply and (
        args.expected_conversations is None
        or args.expected_links is None
        or args.actor_id is None
        or os.environ.get("SELLORA_ALLOW_TTN_BULK_APPLY") != "EXPLICITLY_APPROVED"
    ):
        raise SystemExit("BLOCKED: apply requires owner-approved counters, actor and allow flag")

    with SessionLocal() as db:
        db.execute(text("SET LOCAL statement_timeout = '8000ms'"))
        db.execute(text("SET LOCAL lock_timeout = '2000ms'"))
        if not args.apply:
            db.execute(text("SET TRANSACTION READ ONLY"))
        service = DirectTtnEvidenceService(db)
        conversation_ids = db.scalars(
            select(DirectConversation.id)
            .where(
                DirectConversation.workspace_id == args.workspace_id,
                DirectConversation.deleted_at.is_(None),
            )
            .order_by(DirectConversation.id)
        ).all()
        candidates: list[tuple[UUID, set[UUID]]] = []
        review_only = 0
        truncated = 0
        total_links = 0
        for conversation_id in conversation_ids:
            state = service.preview(args.workspace_id, conversation_id)
            if state is None:
                continue
            if state["scan_truncated"]:
                truncated += 1
            if state["needs_review"]:
                review_only += 1
            ids = {row["order_id"] for row in state["verified_orders"]}
            if ids:
                candidates.append((conversation_id, ids))
                total_links += len(state["verified_orders"])
        print("CONVERSATIONS_SCANNED", len(conversation_ids))
        print("CONVERSATIONS_WITH_VERIFIED_ORDER", len(candidates))
        print("EXACT_TTN_SHIPMENT_LINKS", total_links)
        print("CONVERSATIONS_WITH_REVIEW_ITEMS", review_only)
        print("TRUNCATED_CONVERSATIONS", truncated)
        if not args.apply:
            db.rollback()
            print("DRY_RUN_ONLY_NO_DATABASE_CHANGES")
            return

        if truncated or (
            args.expected_conversations != len(candidates)
            or args.expected_links != total_links
        ):
            db.rollback()
            raise SystemExit("BLOCKED: evidence counts differ or some scans are incomplete")
        created = 0
        reused = 0
        for conversation_id, order_ids in candidates:
            result = service.confirm(
                args.workspace_id, conversation_id, order_ids, args.actor_id
            )
            created += result["created_links"]
            reused += result["existing_links"]
        db.commit()
        print("CONFIRMED_LINKS_CREATED", created)
        print("PREEXISTING_LINKS_REUSED", reused)
        print("APPLY_SUCCESS_NO_ORDER_OR_PAYMENT_MUTATION")


if __name__ == "__main__":
    main()