# Nova Poshta — continuous external TTN discovery

The `nova_poshta_external_documents` inbox stores provider documents without fabricating an order, customer, payment, revenue or profit.

**API:** `GET /api/v1/integrations/nova-poshta/external-documents?match_state=UNMATCHED` (MANAGER+); `POST /api/v1/integrations/nova-poshta/external-documents/scan` (OWNER+, JSON `{"from_date":"2026-10-27","to_date":"2026-10-28","dry_run":true}`). Default scan is preview. One scan covers at most 7 days, and listing is bounded to 10 pages of 100 entries/day.

The import is provider-read-only. Only workspace-scoped inbox records are added. An exact TTN can reference an existing Sellora shipment; conflicts and unknown TTNs remain separate. No payments, order transitions, or inventory actions are inferred by the inbox.

**Rollout gate:**
1. Back up and confirm the current production database. Run migration `202610280050` in disposable PostgreSQL first; do not downgrade a populated inbox.
2. Verify sender's API key and recent provider TTNs in a controlled account using scan preview. Validate paginated provider results.
3. Run `python -m app.services.nova_poshta_inbox_worker --dry-run` and `python -m app.services.nova_poshta_tracking_worker --dry-run` to inspect eligible counts with zero provider writes.
4. After production readiness, explicitly enable `SELLORA_NP_EXTERNAL_SYNC_ENABLED=true` for external discovery and `SELLORA_NP_TRACKING_SYNC_ENABLED=true` for already-linked TTN status updates. Schedule both every 15 minutes; respect throttling and failed-run alerts.
5. Monitor `NP_EXTERNAL_INBOX_SUMMARY` and `NP_TRACKING_SUMMARY`. A successful API key check MUST NOT be displayed as a new delivery status sync.

**Limits:** The existing tracking worker processes 10 shipments/run. The initial 266 pending TTNs therefore need many runs, with rate limits. Inbox items without an exact existing shipment remain `UNMATCHED`, not synthetic sales. No carrier TTN is created or cancelled.
