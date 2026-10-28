"""Ingest read-only provider TTN listings without inventing orders, payments or revenue."""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from app.integrations.nova_poshta_client import NovaPoshtaClient, NovaPoshtaClientError
from app.models.integration_connection import IntegrationStatus
from app.repositories.nova_poshta_external_repository import NovaPoshtaExternalRepository
from app.services.nova_poshta_service import NovaPoshtaSettingsService, NovaPoshtaServiceError

MAX_DAYS = 7
UKRAINE_TZ = ZoneInfo("Europe/Kyiv")
PAGE_SIZE = 100
MAX_PAGES_PER_DAY = 10


class NovaPoshtaExternalInboxService:
    def __init__(self, db, *, client_factory=None):
        self.db = db
        self.repo = NovaPoshtaExternalRepository(db)
        self.settings = NovaPoshtaSettingsService(db)
        self.client_factory = client_factory or (lambda key: NovaPoshtaClient(key))

    def list(self, workspace_id: UUID, *, state: str | None = None):
        return self.repo.list_for_workspace(workspace_id, state=state)

    def collect(self, workspace_id: UUID, from_date: date, to_date: date, *, dry_run: bool = False) -> dict:
        if from_date > to_date or (to_date - from_date).days >= MAX_DAYS or to_date > datetime.now(UKRAINE_TZ).date():
            raise ValueError("NOVA_POSHTA_SCAN_RANGE_INVALID")
        connection, key = self.settings._require_connection(workspace_id)
        if connection.status != IntegrationStatus.CONNECTED.value:
            raise NovaPoshtaServiceError("NOVA_POSHTA_NOT_CONNECTED")
        client = self.client_factory(key)
        candidates = {}
        day = from_date
        while day <= to_date:
            for page in range(1, MAX_PAGES_PER_DAY + 1):
                # Provider read only. The entire page set must be fetched before any DB write.
                rows = client.list_internet_documents(day, day, page=page, limit=PAGE_SIZE)
                if len(rows) > PAGE_SIZE:
                    raise NovaPoshtaClientError("Provider page size unexpected", code="NOVA_POSHTA_LIST_PAGE_INVALID")
                for entry in rows:
                    if entry.tracking_number in candidates and candidates[entry.tracking_number].document_ref not in (None, entry.document_ref):
                        raise NovaPoshtaClientError("Conflicting external TTN identity", code="NOVA_POSHTA_LIST_CONFLICT")
                    candidates[entry.tracking_number] = entry
                if len(rows) < PAGE_SIZE:
                    break
                if page == MAX_PAGES_PER_DAY:
                    raise NovaPoshtaClientError("Provider listing truncated", code="NOVA_POSHTA_LIST_TRUNCATED")
            day += timedelta(days=1)

        counters = {"scanned": len(candidates), "unmatched": 0, "linked": 0, "conflicts": 0, "dry_run": dry_run}
        now = datetime.now(UTC)
        for number, entry in candidates.items():
            matches = self.repo.matching_shipment_ids(workspace_id, number)
            match_state = "LINKED" if len(matches) == 1 else "CONFLICT" if matches else "UNMATCHED"
            counters[{"LINKED": "linked", "CONFLICT": "conflicts", "UNMATCHED": "unmatched"}[match_state]] += 1
            if not dry_run:
                self.repo.upsert(
                    workspace_id, number, entry.document_ref, entry.status,
                    match_state, matches[0] if len(matches) == 1 else None, now,
                )
        if dry_run:
            self.db.rollback()
        else:
            self.db.commit()
        return counters
