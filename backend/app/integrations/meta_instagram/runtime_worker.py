from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import logging
import os
import time

from sqlalchemy import select

from app.ai.services.direct_customer_data_extraction_service import (
    DirectCustomerDataExtractionService,
    PROMPT_KEY as CUSTOMER_EXTRACTION_PROMPT_KEY,
)
from app.database.session import SessionLocal
from app.integrations.meta_instagram.services.history_sync_visibility_service import (
    InstagramHistorySyncVisibilityService as InstagramHistorySyncService,
)
from app.integrations.meta_instagram.services.webhook_processor_service import InstagramWebhookProcessorService
from app.models.ai_direct import AIAnalysis, AIAnalysisStatus

logger = logging.getLogger(__name__)


AI_EXTRACTION_COOLDOWNS = {
    "AI_RATE_LIMITED": timedelta(minutes=1),
    "AI_BILLING_QUOTA_EXCEEDED": timedelta(hours=6),
    "AI_PROVIDER_CREDENTIAL_INVALID": timedelta(hours=6),
    "AI_PROVIDER_FORBIDDEN": timedelta(hours=6),
    "AI_PROVIDER_UNAVAILABLE": timedelta(minutes=5),
    "AI_REQUEST_TIMEOUT": timedelta(minutes=5),
}


def webhook_worker_enabled() -> bool:
    return os.getenv("META_INSTAGRAM_WEBHOOK_WORKER_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def webhook_poll_seconds() -> float:
    raw = os.getenv("META_INSTAGRAM_WEBHOOK_POLL_SECONDS", "5")
    try:
        return min(max(float(raw), 1.0), 60.0)
    except ValueError:
        return 5.0


def customer_extraction_poll_seconds() -> float:
    raw = os.getenv("AI_CUSTOMER_DATA_EXTRACTION_POLL_SECONDS", "30")
    try:
        return min(max(float(raw), 10.0), 300.0)
    except ValueError:
        return 30.0


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


def _customer_extraction_cooldown_active(db) -> bool:
    latest_failure = db.execute(
        select(AIAnalysis)
        .where(
            AIAnalysis.prompt_key == CUSTOMER_EXTRACTION_PROMPT_KEY,
            AIAnalysis.status == AIAnalysisStatus.FAILED_SAFE.value,
            AIAnalysis.safe_error_code.in_(tuple(AI_EXTRACTION_COOLDOWNS)),
        )
        .order_by(AIAnalysis.completed_at.desc().nullslast(), AIAnalysis.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if latest_failure is None:
        return False
    cooldown = AI_EXTRACTION_COOLDOWNS.get(latest_failure.safe_error_code)
    failure_time = latest_failure.completed_at or latest_failure.created_at
    return bool(cooldown and failure_time and datetime.now(UTC) < failure_time + cooldown)


async def process_customer_data_extraction_job() -> str | None:
    with SessionLocal() as db:
        try:
            if _customer_extraction_cooldown_active(db):
                return None
            status = await DirectCustomerDataExtractionService(db).process_next()
            db.commit()
            return status
        except Exception:
            db.rollback()
            raise


async def run_instagram_webhook_worker(stop_event: asyncio.Event) -> None:
    interval = webhook_poll_seconds()
    extraction_interval = customer_extraction_poll_seconds()
    next_extraction_at = 0.0
    logger.info(
        "Instagram webhook worker started",
        extra={
            "poll_seconds": interval,
            "ai_customer_extraction_poll_seconds": extraction_interval,
        },
    )
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

        monotonic_now = time.monotonic()
        if monotonic_now >= next_extraction_at:
            next_extraction_at = monotonic_now + extraction_interval
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
