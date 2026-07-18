import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const read = (path) => readFileSync(join(root, path), "utf8");
const failures = [];
function has(path, marker, label = marker) {
  if (!read(path).includes(marker)) failures.push(`Missing ${label} in ${path}`);
}

const stagingDoc = "docs/nova-poshta-staging-validation.md";
const workflowDoc = "docs/shipment-workflow.md";
const knownLimitations = "docs/known-limitations.md";
const stagingChecklist = "docs/staging-qa-checklist.md";
const pilotChecklist = "docs/pilot-qa-checklist.md";
const mvpReadiness = "docs/mvp-readiness.md";
const settingsCard = "frontend/src/features/integrations/components/nova-poshta-settings-card.tsx";
const citySelect = "frontend/src/features/integrations/components/city-search-select.tsx";
const warehouseSelect = "frontend/src/features/integrations/components/warehouse-search-select.tsx";
const ttnButton = "frontend/src/features/integrations/components/create-ttn-button.tsx";
const ttnActions = "frontend/src/features/shipments/components/ttn-actions.tsx";
const shipmentPanel = "frontend/src/features/integrations/components/nova-poshta-shipment-panel.tsx";
const novaService = "backend/app/services/nova_poshta_service.py";
const novaTests = "backend/tests/test_nova_poshta.py";
const shipmentTests = "backend/tests/test_shipments.py";
const shipmentApi = "backend/app/api/v1/shipments.py";
const novaApi = "backend/app/api/v1/nova_poshta.py";
const uk = "frontend/src/i18n/messages/uk.json";
const en = "frontend/src/i18n/messages/en.json";

// Staging validation checklist and edge-case docs.
[
  "Open the staging frontend",
  "Confirm only the masked key is shown after save",
  "Create TTN only if safe to do so",
  "Credential edge cases",
  "Sender settings edge cases",
  "Recipient and customer edge cases",
  "TTN edge cases",
  "Delivery status sync edge cases",
  "RBAC and workspace validation",
  "Audit and logging safety",
  "Mobile QA",
].forEach((marker) => has(stagingDoc, marker));

// Credential and sender settings UX markers.
has(settingsCard, "masked_api_key", "masked saved credential state");
has(settingsCard, "setSenderWarehouseRef(\"\")", "stale sender warehouse clearing");
has(settingsCard, "required={!hasSavedKey}", "first credential required only without saved key");
has(citySelect, "minCityQuery", "minimum city query state");
has(warehouseSelect, "disabled={!cityRef}", "warehouse disabled before city selection");
has(warehouseSelect, "selectCityFirst", "select city first helper");

// Recipient/customer, TTN and status-sync safe handling.
has(ttnButton, "recipientPhoneRequired");
has(ttnButton, "recipientCityRequired");
has(ttnButton, "recipientWarehouseRequired");
has(ttnButton, "NOVA_POSHTA_TTN_INCOMPLETE");
has(ttnButton, "createInFlight.current", "synchronous duplicate TTN guard");
has(ttnButton, "disabled={create.isPending || createInFlight.current || hasTtn || manualHold}", "duplicate/loading create TTN disabled");
has(ttnButton, "disabled={sync.isPending || !hasTtn}", "sync disabled without TTN");
has(shipmentPanel, "recipientAddressRequired");
has(ttnActions, "navigator.clipboard.writeText", "copy TTN action");

// Backend safe edge-case handling and tests.
has(novaService, "TTN_CREATE_INCOMPLETE");
has(novaService, "NOVA_POSHTA_TTN_INCOMPLETE");
has(novaService, "NOVA_POSHTA_STATUS_UNAVAILABLE");
has(novaService, "Shipment does not have a Nova Poshta tracking number");
has(novaTests, "test_create_ttn_incomplete_response_is_safe_and_does_not_store_tracking");
has(novaTests, "test_sync_status_without_tracking_is_blocked_before_api_call");
has(novaTests, "test_sync_status_empty_response_returns_safe_unavailable_message");
has(novaTests, "test_cross_workspace_ttn_access_uses_workspace_scoped_connection_and_shipment");
has(novaTests, "synthetic-credential-value");
has(shipmentTests, "test_shipment_creation_blocks_order_without_customer");

// RBAC and workspace isolation markers.
has(shipmentApi, "require_min_role(RoleName.MANAGER)");
has(shipmentApi, "require_min_role(RoleName.ANALYST)");
has(novaApi, "require_min_role(RoleName.OWNER)");
has(novaApi, "require_min_role(RoleName.MANAGER)");
has(novaService, "get_by_provider(workspace_id");
has(novaService, "self.shipments.get(workspace_id, shipment_id)");

// Localized error messages.
[
  "apiKeyMissing",
  "apiKeyInvalid",
  "senderSettingsRequiredBeforeTtn",
  "keySavedMasked",
].forEach((key) => {
  has(uk, `"${key}"`, `Ukrainian ${key}`);
  has(en, `"${key}"`, `English ${key}`);
});
[
  "recipientPhoneRequired",
  "recipientCityRequired",
  "recipientWarehouseRequired",
  "createTtnIncomplete",
].forEach((key) => {
  has(uk, `"${key}"`, `Ukrainian ${key}`);
  has(en, `"${key}"`, `English ${key}`);
});

// Docs updates and limitations.
has(workflowDoc, "Sprint 3.2 staging edge-case stabilization");
has(knownLimitations, "Sprint 8E Nova Poshta limitations");
has(stagingChecklist, "Sprint 3.2");
has(pilotChecklist, "Sprint 3.2");
has(mvpReadiness, "Sprint 8E Nova Poshta readiness update");

// No raw production credential fixture markers in docs/source regression scope.
const forbidden = ["real-nova-poshta-api-key", "actual-api-key", "live-ttn-value", "Authorization: Bearer"];
for (const file of [stagingDoc, workflowDoc, ttnButton, novaTests]) {
  for (const marker of forbidden) {
    if (read(file).includes(marker)) failures.push(`Forbidden raw credential marker ${marker} in ${file}`);
  }
}

if (failures.length) {
  console.error("Nova Poshta staging edge-case regression failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}
console.log("Nova Poshta staging edge-case regression passed.");
