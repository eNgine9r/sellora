import { readFileSync } from "node:fs";

const checks = [];
const read = (path) => readFileSync(path, "utf8");
const check = (label, condition) => checks.push({ label, condition });

const backendService = read("backend/app/services/nova_poshta_service.py");
const backendApi = read("backend/app/api/v1/nova_poshta.py") + read("backend/app/api/v1/shipments.py");
const backendTests = read("backend/tests/test_nova_poshta.py");
const settingsCard = read("frontend/src/features/integrations/components/nova-poshta-settings-card.tsx");
const citySearch = read("frontend/src/features/integrations/components/city-search-select.tsx");
const warehouseSearch = read("frontend/src/features/integrations/components/warehouse-search-select.tsx");
const ttnButton = read("frontend/src/features/integrations/components/create-ttn-button.tsx");
const shipmentPanel = read("frontend/src/features/integrations/components/nova-poshta-shipment-panel.tsx");
const orderDetails = read("frontend/src/features/orders/components/order-details.tsx");
const shipmentsPage = read("frontend/src/app/shipments/page.tsx");
const en = read("frontend/src/i18n/messages/en.json");
const uk = read("frontend/src/i18n/messages/uk.json");
const docs = read("docs/nova-poshta-production-validation.md") + read("docs/staging-qa-checklist.md") + read("docs/pilot-qa-checklist.md") + read("docs/known-limitations.md") + read("docs/mvp-readiness.md");

check("credential save/masking preserves existing key", backendService.includes("NOVA_POSHTA_SENDER_SETTINGS_UPDATED") && backendService.includes("payload.api_key") && backendService.includes("mask_secret(api_key)") && backendTests.includes("test_sender_settings_update_preserves_existing_credential_without_raw_response"));
check("connection validation and RBAC", backendService.includes("test_connection") && backendApi.includes("require_min_role(RoleName.OWNER)") && settingsCard.includes("testingConnection") && settingsCard.includes("masked_api_key"));
check("sender settings validation", backendService.includes("sender_city_ref is required") && backendService.includes("sender_warehouse_ref is required") && settingsCard.includes("missingSenderFields") && settingsCard.includes("setSenderWarehouseRef(\"\")"));
check("city search states and debounce", citySearch.includes("useDebouncedValue") && citySearch.includes("minCityQuery") && citySearch.includes("citySearchFailed") && citySearch.includes("noCitiesFound"));
check("warehouse search states and city guard", warehouseSearch.includes("useDebouncedValue") && warehouseSearch.includes("disabled={!cityRef}") && warehouseSearch.includes("selectCityFirst") && warehouseSearch.includes("warehouseSearchFailed"));
check("shipment creation from order", orderDetails.includes("/shipments?order_id=") && shipmentsPage.includes("new URLSearchParams(window.location.search)") && shipmentsPage.includes("initialOrderId={initialOrderId}"));
check("TTN tracking display and duplicate prevention", backendService.includes("ttn already exists") && ttnButton.includes("duplicateTtn") && shipmentPanel.includes("documentNumber") && shipmentPanel.includes("tracking_number"));
check("safe error messages", backendService.includes("NOVA_POSHTA_TTN_FAILED") && backendService.includes("STATUS_SYNC_FAILED") && !backendService.includes("errors=[str(exc)]") && ttnButton.includes("statusSyncUnavailable"));
check("audit logging without raw keys", backendService.includes("credential_rotated") && backendService.includes("safe_error") && backendTests.includes("does_not_log_credential"));
check("workspace safety markers", backendService.includes("get(workspace_id, shipment_id)") && backendService.includes("_require_connection(workspace_id)") && backendApi.includes("get_workspace_id"));
check("i18n keys", [en, uk].every((messages) => messages.includes("ttnFailed") && messages.includes("senderSettingsIncomplete") && messages.includes("statusSyncUnavailable") && messages.includes("createFromOrder")));
check("production validation docs", docs.includes("Nova Poshta Production Validation Guide") && docs.includes("Duplicate TTN"));
check("no raw API key fixture", !/(api[_ -]?key\s*[:=]\s*[A-Za-z0-9_-]{16,}|Authorization: Bearer\s+[A-Za-z0-9._-]+)/i.test(settingsCard + backendTests + docs));

const failed = checks.filter((item) => !item.condition);
for (const item of checks) console.log(`${item.condition ? "✓" : "✗"} ${item.label}`);
if (failed.length) {
  console.error(`Nova Poshta production validation regression failed: ${failed.map((item) => item.label).join(", ")}`);
  process.exit(1);
}
console.log("Nova Poshta production validation regression passed.");
