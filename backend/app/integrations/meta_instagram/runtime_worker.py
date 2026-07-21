from __future__ import annotations

import asyncio
import logging
import os

from app.ai.services.direct_customer_data_extraction_service import (
    DirectCustomerDataExtractionService,
)
from app.database.session import SessionLocal
from app.integrations.meta_instagram.services.history_sync_visibility_service import (
    InstagramHistorySyncVisibilityService as InstagramHistorySyncService,
)
from app.integrations.meta_instagram.services.webhook_processor_service import InstagramWebhookProcessorService

logger = logging.getLogger(__name__)


def webhook_worker_enabled() -> bool:
    return os.getenv("META_INSTAGRAM_WEBHOOK_WORKER_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def webhook_poll_seconds() -> float:
    raw = os.getenv("META_INSTAGRAM_WEBHOOK_POLL_SECONDS", "5")
    try:
        return min(max(float(raw), 1.0), 60.0)
    except ValueError:
        return 5.0


def process_webhook_batch() -> int:
    with SessionLocal() as db:
        try:
            processed = InstagramWebhookProcessorService(db).process_batch()
            db.commit()
            return processed
        except Exception:
            db.rollback()
            raise


async def process_history_sync_job() -> str | None:
    with SessionLocal() as db:
        try:
            sync = await InstagramHistorySyncService(db).process_next()
            db.commit()
            return sync.status if sync else None
        except Exception:
            db.rollback()
            raise


async def process_customer_data_extraction_job() -> str | None:
    with SessionLocal() as db:
        try:
            status = await DirectCustomerDataExtractionService(db).process_next()
            db.commit()
            return status
        except Exception:
            db.rollback()
            raise


async def run_instagram_webhook_worker(stop_event: asyncio.Event) -> None:
    interval = webhook_poll_seconds()
    logger.info("Instagram webhook worker started", extra={"poll_seconds": interval})
    while not stop_event.is_set():
        try:
            processed = await asyncio.to_thread(process_webhook_batch)
            if processed:
                logger.info("Instagram webhook batch processed", extra={"processed": processed})
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Instagram webhook worker batch failed")

        try:
            history_status = await process_history_sync_job()
            if history_status:
                logger.info(
                    "Instagram history sync job processed",
                    extra={"status": history_status},
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Instagram history sync job failed")

        try:
            extraction_status = await process_customer_data_extraction_job()
            if extraction_status:
                logger.info(
                    "Direct customer data extraction processed",
                    extra={"status": extraction_status},
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Direct customer data extraction failed")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except TimeoutError:
            pass
    logger.info("Instagram webhook worker stopped")
