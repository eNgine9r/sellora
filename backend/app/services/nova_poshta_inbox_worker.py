"""Bounded background ingestion of external TTNs (provider read-only).

Run periodically: python -m app.services.nova_poshta_inbox_worker
Requires SELLORA_NP_EXTERNAL_SYNC_ENABLED=true; --dry-run performs no provider calls.
"""
import argparse
import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text

from app.database.session import SessionLocal, engine
from app.repositories.nova_poshta_external_repository import NovaPoshtaExternalRepository
from app.services.nova_poshta_external_inbox_service import NovaPoshtaExternalInboxService

LOCK_ID = 846529472002
log = logging.getLogger(__name__)


def enabled() -> bool:
    return os.getenv("SELLORA_NP_EXTERNAL_SYNC_ENABLED", "false").lower() in ("true", "1", "on", "yes")


def run_once(*, dry_run: bool = False):
    if not dry_run and not enabled():
        raise RuntimeError("External NP sync is not enabled")
    stats = {"workspaces": 0, "scanned": 0, "linked": 0, "unmatched": 0, "conflicts": 0, "failed": 0, "locked": False, "dry_run": dry_run}
    with engine.connect() as conn:
        if not conn.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_ID}):
            stats["locked"] = True
            return stats
        try:
            with SessionLocal() as db:
                workspaces = NovaPoshtaExternalRepository(db).workspaces_ready()
            stats["workspaces"] = len(workspaces)
            if dry_run:
                return stats
            today = datetime.now(ZoneInfo("Europe/Kyiv")).date()
            # An overlapping 3-day window safely captures delayed provider documents.
            for workspace_id in workspaces:
                with SessionLocal() as db:
                    try:
                        result = NovaPoshtaExternalInboxService(db).collect(
                            workspace_id, today - timedelta(days=2), today
                        )
                        for key in ("scanned", "linked", "unmatched", "conflicts"):
                            stats[key] += result[key]
                    except Exception as exc:
                        db.rollback()
                        stats["failed"] += 1
                        # Never log tracking numbers, names, phone numbers, provider raw responses or secrets.
                        log.warning("External NP scan failed (%s)", type(exc).__name__)
        finally:
            conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_ID})
    return stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    stats = run_once(dry_run=args.dry_run)
    print("NP_EXTERNAL_INBOX_SUMMARY " + " ".join(f"{k}={v}" for k, v in stats.items()))
    if not args.dry_run and stats["failed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
