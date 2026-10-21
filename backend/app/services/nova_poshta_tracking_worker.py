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

from sqlalchemy import or_, select, text

from app.database.session import SessionLocal, engine
from app.models.integration_connection import IntegrationConnection, IntegrationProvider, IntegrationStatus
from app.models.shipment import Shipment, ShipmentCarrier, ShipmentStatus
from app.models.workspace import Workspace
from app.services.nova_poshta_provider_service import NovaPoshtaProviderShipmentService

log = logging.getLogger(__name__)
# Reserved for tracking only; avoids duplicate simultaneous CLI timers.
LOCK_ID = 846529472001
BATCH_LIMIT = 10
MIN_INTERVAL = timedelta(minutes=20)
MAX_AGE = timedelta(days=90)


def enabled() -> bool:
    return os.getenv("SELLORA_NP_TRACKING_SYNC_ENABLED", "false").strip().lower() in ("true", "1", "yes", "on")


def pending_tracking_ids(db, *, now: datetime, limit: int = BATCH_LIMIT) -> list[tuple[UUID, UUID]]:
    """Find recent, nonterminal, provider-backed TTNs in connected workspaces."""
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
        .where(
            Shipment.deleted_at.is_(None),
            Shipment.carrier == ShipmentCarrier.NOVA_POSHTA.value,
            Shipment.nova_poshta_document_number.isnot(None),
            Shipment.status.in_([
                ShipmentStatus.CREATED.value, ShipmentStatus.IN_TRANSIT.value,
                ShipmentStatus.ARRIVED.value,
            ]),
            Shipment.created_at >= now - MAX_AGE,
            or_(
                Shipment.nova_poshta_synced_at.is_(None),
                Shipment.nova_poshta_synced_at <= now - MIN_INTERVAL,
            ),
        )
        .order_by(Shipment.nova_poshta_synced_at.asc().nullsfirst(), Shipment.created_at.asc())
        .limit(min(max(limit, 1), BATCH_LIMIT))
    )
    return list(db.execute(stmt).all())


def run_once(*, dry_run: bool = False) -> dict[str, int | bool]:
    if not dry_run and not enabled():
        raise RuntimeError("Background tracking is not enabled")
    counters: dict[str, int | bool] = {
        "eligible": 0, "checked": 0, "synced": 0, "failed": 0, "dry_run": dry_run, "locked": False,
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
                        if result.success:
                            counters["synced"] = int(counters["synced"]) + 1
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
