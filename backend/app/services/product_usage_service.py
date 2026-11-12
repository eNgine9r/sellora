import logging
from datetime import UTC, datetime, time, timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.product_usage import DROPPED_EVENTS, UsageEvent, UsageSource
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.platform_admin_repository import PlatformWorkspaceRepository
from app.repositories.product_usage_repository import ProductUsageRepository
from app.schemas.product_usage import ProductUsageReport, ProductUsageTotals

logger = logging.getLogger(__name__)


def _coverage_start() -> datetime | None:
    settings = get_settings()
    if settings.product_usage_capture_enabled and settings.product_usage_coverage_from is not None:
        return settings.product_usage_coverage_from.astimezone(UTC)
    return None


class ProductUsageWriter:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.usage = ProductUsageRepository(db)
        self.audit = AuditLogRepository(db)

    def workspace_activated(self, workspace_id: UUID) -> None:
        self._capture(workspace_id, UsageEvent.WORKSPACE_ACTIVATED, UsageSource.WORKSPACE, workspace_id)

    def product_created(self, workspace_id: UUID, product_id: UUID) -> None:
        self._capture(workspace_id, UsageEvent.FIRST_PRODUCT, UsageSource.CATALOG, product_id)

    def order_created(self, workspace_id: UUID, order_id: UUID) -> None:
        self._capture(workspace_id, UsageEvent.ORDER_CREATED, UsageSource.ORDERS, order_id)

    def integration_used(self, workspace_id: UUID, source: UsageSource) -> None:
        self._capture(workspace_id, UsageEvent.INTEGRATION_USED, source)

    def _capture(
        self, workspace_id: UUID, event: UsageEvent, source: UsageSource, entity_id: UUID | None = None,
    ) -> None:
        coverage_start = _coverage_start()
        now = datetime.now(UTC)
        if coverage_start is None or now < coverage_start:
            return
        # Flush domain changes before the savepoint. Domain errors retain their normal handling.
        self.db.flush()
        try:
            with self.db.begin_nested():
                previous_timeout = self.usage.set_capture_lock_timeout()
                self._record(workspace_id, event, source, entity_id, now)
                self.usage.restore_lock_timeout(previous_timeout)
        except Exception:
            if not self.db.is_active:
                raise
            logger.warning("Product usage operation dropped (%s)", event.value)
            try:
                with self.db.begin_nested():
                    previous_timeout = self.usage.set_capture_lock_timeout()
                    self.usage.increment_daily(workspace_id, now.date(), DROPPED_EVENTS)
                    self.usage.restore_lock_timeout(previous_timeout)
            except Exception:
                if not self.db.is_active:
                    raise
                logger.warning("Product usage could not persist its coverage marker")

    def _record(
        self, workspace_id: UUID, event: UsageEvent, source: UsageSource, entity_id: UUID | None, now: datetime,
    ) -> None:
        if self.audit.has_demo_workspace_provenance(workspace_id):
            return
        if event == UsageEvent.INTEGRATION_USED:
            self.usage.record(workspace_id, event, source, f"{source.value}:{now.date().isoformat()}", now)
            return
        if event == UsageEvent.FIRST_PRODUCT:
            if entity_id is not None and not self.usage.other_product_exists(workspace_id, entity_id):
                self.usage.record(workspace_id, event, source, workspace_id.hex, now)
            return
        if event == UsageEvent.ORDER_CREATED and entity_id is not None:
            self.usage.record(workspace_id, event, source, entity_id.hex, now)
            if not self.usage.other_order_exists(workspace_id, entity_id):
                self.usage.record(workspace_id, UsageEvent.FIRST_ORDER, source, workspace_id.hex, now)
            return
        self.usage.record(workspace_id, event, source, workspace_id.hex, now)


class ProductUsageService:
    def __init__(self, db: Session) -> None:
        self.usage = ProductUsageRepository(db)
        self.workspaces = PlatformWorkspaceRepository(db)
        self.audit = AuditLogRepository(db)

    def get_report(
        self, days: Literal[7, 30], *, workspace_id: UUID | None = None, now: datetime | None = None,
    ) -> ProductUsageReport | None:
        as_of = (now or datetime.now(UTC)).astimezone(UTC)
        to_day = as_of.date()
        from_day = to_day - timedelta(days=days - 1)
        coverage_from = _coverage_start()
        report = ProductUsageReport(
            days=days, from_day=from_day, to_day=to_day, as_of=as_of,
            coverage_from=coverage_from, coverage="unavailable",
        )
        if workspace_id is not None:
            if not self.workspaces.exists(workspace_id):
                return None
            if self.audit.has_demo_workspace_provenance(workspace_id):
                return report
        if coverage_from is None or as_of < coverage_from:
            return report
        # Counts from the rollout's partial first day cannot be separated from a prior capture window.
        first_covered_day = coverage_from.date() + timedelta(days=coverage_from.time() != time.min)
        first_reported_day = max(from_day, first_covered_day)
        if first_reported_day > to_day:
            return report
        totals = dict(self.usage.totals(first_reported_day, to_day, workspace_id))
        dropped = int(totals.pop("dropped_operations"))
        return report.model_copy(update={
            "coverage": "partial" if first_reported_day > from_day or dropped else "complete",
            "dropped_operations": dropped,
            "totals": ProductUsageTotals(**totals),
        })
