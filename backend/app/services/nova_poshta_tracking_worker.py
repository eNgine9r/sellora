"""Bounded, provider-read-only periodic status synchronization.

Run via: python -m app.services.nova_poshta_tracking_worker [--dry-run].
The command cannot create, change or delete TTNs. It can persist delivery status
and authorized order/inventory transitions based on provider tracking evidence.
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import logging
import os
from uuid import UUID

from sqlalchemy import String, and_, cast, func, or_, select, text

from app.database.session import SessionLocal, engine
from app.models.audit_log import AuditLog
from app.models.integration_connection import IntegrationConnection, IntegrationProvider, IntegrationStatus
from app.models.shipment import Shipment, ShipmentCarrier, ShipmentStatus
from app.models.workspace import Workspace
from app.services.nova_poshta_provider_service import NovaPoshtaProviderShipmentService

log = logging.getLogger(__name__)
# Reserved for tracking only; avoids duplicate simultaneous CLI timers.
LOCK_ID = 846529472001
BATCH_LIMIT = 10
MIN_INTERVAL = timedelta(minutes=20)
NOT_FOUND_RETRY_INTERVAL = timedelta(hours=24)
MAX_AGE = timedelta(days=90)


def enabled() -> bool:
    return os.getenv("SELLORA_NP_TRACKING_SYNC_ENABLED", "false").strip().lower() in ("true", "1", "yes", "on")


def pending_tracking_ids(db, *, now: datetime, limit: int = BATCH_LIMIT) -> list[tuple[UUID, UUID]]:
    """Find recently active, nonterminal, provider-backed TTNs in connected workspaces."""
    # Fair scheduling: provider code 3 (number not found) is unverified,
    # so nova_poshta_synced_at stays NULL; never re-check the same 10 indefinitely.
    # Audit attempts are already written by the provider service, including
    # failures; use them as a read-only retry ledger across restarts.
    attempts = (
        select(
            AuditLog.workspace_id.label("workspace_id"),
            AuditLog.entity_id.label("entity_id"),
            func.max(AuditLog.created_at).label("last_attempt"),
        )
        .where(
            AuditLog.entity_type == "Shipment",
            AuditLog.action.in_(
                ["NOVA_POSHTA_STATUS_SYNCED", "NOVA_POSHTA_STATUS_UNVERIFIED",
                 "NOVA_POSHTA_STATUS_UNAVAILABLE", "NOVA_POSHTA_ERROR"]
            ),
        )
        .group_by(AuditLog.workspace_id, AuditLog.entity_id)
        .subquery()
    )
    # A provider response with code 3 is NOT evidence of delivery.
    # Retrying that missing/invalid number every 20 minutes wastes carrier quota
    # and can starve real newly created shipments. Keep it for manual review,
    # retry at most daily, and prioritize never-attempted TTNs.
    code3 = (
        select(
            AuditLog.workspace_id.label("workspace_id"),
            AuditLog.entity_id.label("entity_id"),
            func.max(AuditLog.created_at).label("last_not_found"),
        )
        .where(
            AuditLog.entity_type == "Shipment",
            AuditLog.action == "NOVA_POSHTA_STATUS_UNVERIFIED",
            AuditLog.new_value["provider_status_code"].astext == "3",
        )
        .group_by(AuditLog.workspace_id, AuditLog.entity_id)
        .subquery()
    )
    stmt = (
        select(Shipment.workspace_id, Shipment.id)
        .join(
            Workspace,
            (Workspace.id == Shipment.workspace_id)
            & (Workspace.is_active.is_(True)),
        )
        .join(
            IntegrationConnection,
            (IntegrationConnection.workspace_id == Shipment.workspace_id)
            & (IntegrationConnection.provider == IntegrationProvider.NOVA_POSHTA.value)
            & (IntegrationConnection.status == IntegrationStatus.CONNECTED.value)
            & (IntegrationConnection.deleted_at.is_(None)),
        )
        .outerjoin(
            attempts,
            and_(
                attempts.c.workspace_id == Shipment.workspace_id,
                attempts.c.entity_id == cast(Shipment.id, String),
            ),
        )
        .outerjoin(
            code3,
            and_(
                code3.c.workspace_id == Shipment.workspace_id,
                code3.c.entity_id == cast(Shipment.id, String),
            ),
        )
        .where(
            Shipment.deleted_at.is_(None),
            Shipment.carrier == ShipmentCarrier.NOVA_POSHTA.value,
            Shipment.nova_poshta_document_number.isnot(None),
            Shipment.status.in_([
                ShipmentStatus.CREATED.value, ShipmentStatus.IN_TRANSIT.value,
                ShipmentStatus.ARRIVED.value,
            ]),
            Shipment.updated_at >= now - MAX_AGE,
            or_(
                code3.c.last_not_found.is_(None),
                code3.c.last_not_found <= now - NOT_FOUND_RETRY_INTERVAL,
            ),
            or_(
                attempts.c.last_attempt.is_(None),
                attempts.c.last_attempt <= now - MIN_INTERVAL,
            ),
            or_(
                Shipment.nova_poshta_synced_at.is_(None),
                Shipment.nova_poshta_synced_at <= now - MIN_INTERVAL,
            ),
        )
        .order_by(
            attempts.c.last_attempt.asc().nullsfirst(),
            Shipment.nova_poshta_synced_at.asc().nullsfirst(),
            Shipment.updated_at.asc(),
        )
        .limit(min(max(limit, 1), BATCH_LIMIT))
    )
    return list(db.execute(stmt).all())


def run_once(*, dry_run: bool = False) -> dict[str, int | bool]:
    if not dry_run and not enabled():
        raise RuntimeError("Background tracking is not enabled")
    counters: dict[str, int | bool] = {
        "eligible": 0, "checked": 0, "synced": 0, "unverified": 0, "failed": 0, "dry_run": dry_run, "locked": False,
    }
    # Keep an advisory session lock for the entire run. Always release.
    with engine.connect() as lock_connection:
        acquired = lock_connection.scalar(text("SELECT pg_try_advisory_lock(:lock)"), {"lock": LOCK_ID})
        if not acquired:
            counters["locked"] = True
            return counters
        try:
            with SessionLocal() as db:
                rows = pending_tracking_ids(db, now=datetime.now(UTC))
            counters["eligible"] = len(rows)
            if dry_run:
                return counters
            seen_shipments = set()
            for workspace_id, shipment_id in rows:
                if (workspace_id, shipment_id) in seen_shipments:
                    continue
                seen_shipments.add((workspace_id, shipment_id))
                with SessionLocal() as db:
                    try:
                        # Re-check recent sync and state after other workers/manual actions.
                        shipment = db.scalar(
                            select(Shipment).where(
                                Shipment.id == shipment_id,
                                Shipment.workspace_id == workspace_id,
                                Shipment.deleted_at.is_(None),
                            )
                        )
                        if (
                            not shipment
                            or
                            shipment.status not in (
                                ShipmentStatus.CREATED.value, ShipmentStatus.IN_TRANSIT.value,
                                ShipmentStatus.ARRIVED.value,
                            )
                            or (shipment.nova_poshta_synced_at and shipment.nova_poshta_synced_at > datetime.now(UTC) - MIN_INTERVAL)
                        ):
                            continue
                        counters["checked"] = int(counters["checked"]) + 1
                        result = NovaPoshtaProviderShipmentService(db).sync_status(workspace_id, shipment_id, None)
                        if result.success and result.synced_at is not None and not result.manual_review_required:
                            counters["synced"] = int(counters["synced"]) + 1
                        elif result.success and result.manual_review_required:
                            counters["unverified"] = int(counters["unverified"]) + 1
                        else:
                            counters["failed"] = int(counters["failed"]) + 1
                    except Exception as exc:
                        db.rollback()
                        counters["failed"] = int(counters["failed"]) + 1
                        # Never log TTN numbers, customer names, payloads, or secret keys.
                        log.warning("Nova Poshta background tracking failed (type=%s)", type(exc).__name__)
        finally:
            lock_connection.execute(text("SELECT pg_advisory_unlock(:lock)"), {"lock": LOCK_ID})
    return counters


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounded Nova Poshta tracking sync")
    parser.add_argument("--dry-run", action="store_true", help="Select candidates without any provider calls or data writes")
    args = parser.parse_args()
    stats = run_once(dry_run=args.dry_run)
    logging.getLogger(__name__).info("Tracking result: %s", stats)
    print("NP_TRACKING_SUMMARY " + " ".join(f"{k}={v}" for k, v in stats.items()))
    if not args.dry_run and stats["failed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
