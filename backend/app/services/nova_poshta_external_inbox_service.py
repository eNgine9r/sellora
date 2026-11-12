"""Ingest read-only provider TTN listings without inventing orders, payments or revenue."""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from app.integrations.nova_poshta_client import NovaPoshtaClient, NovaPoshtaClientError
from app.models.integration_connection import IntegrationStatus
from app.repositories.nova_poshta_external_repository import NovaPoshtaExternalRepository
from app.schemas.nova_poshta_external import NovaPoshtaExternalDocumentResponse
from app.services.nova_poshta_service import NovaPoshtaSettingsService, NovaPoshtaServiceError
from app.models.shipment import ShipmentStatus
from app.services.nova_poshta_tracking import normalize_tracking_status, should_apply_tracking_status

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

    def list_with_direct_evidence(self, workspace_id: UUID, *, state: str | None = None) -> list[dict]:
        """Return safe, workspace-scoped navigation evidence for external TTNs."""
        documents = self.repo.list_for_workspace(workspace_id, state=state)
        evidence = self.repo.direct_evidence_by_document(workspace_id, [doc.id for doc in documents])
        return [
            {
                **NovaPoshtaExternalDocumentResponse.model_validate(doc).model_dump(),
                **evidence.get(doc.id, {}),
            }
            for doc in documents
        ]

    def refresh_tracking(self, workspace_id: UUID, *, limit: int = 12) -> dict[str, int]:
        """Bounded provider-read-only checks; only external TTN evidence is updated.

        Never creates orders, edits payments, or changes inventory. Runs on the
        existing 15-minute external-inbox cadence, not for every browser request.
        """
        _, key = self.settings._require_connection(workspace_id)
        client = self.client_factory(key)
        now = datetime.now(UTC)
        candidates = self.repo.tracking_candidates(workspace_id, now=now, limit=limit)
        counts = {"eligible": len(candidates), "checked": 0, "changed": 0, "unverified": 0, "failed": 0}
        for doc in candidates:
            try:
                result = client.get_document_tracking(doc.tracking_number)
                incoming = normalize_tracking_status(result.code, result.status) if result else None
                doc.provider_tracking_checked_at = datetime.now(UTC)
                counts["checked"] += 1
                if incoming is None:
                    counts["unverified"] += 1
                else:
                    previous = ShipmentStatus(doc.provider_normalized_status) if doc.provider_normalized_status else None
                    if previous is None or incoming == previous or should_apply_tracking_status(previous, incoming):
                        if doc.provider_normalized_status != incoming.value:
                            counts["changed"] += 1
                        doc.provider_normalized_status = incoming.value
                        if result and result.status:
                            doc.provider_status = result.status[:255]
                self.db.commit()
            except NovaPoshtaClientError as exc:
                self.db.rollback()
                counts["failed"] += 1
                if "many requests" in str(getattr(exc, "code", "")).lower():
                    break  # Respect provider cooldown; do not retry aggressively.
            except Exception:
                self.db.rollback()
                counts["failed"] += 1
        return counts

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
