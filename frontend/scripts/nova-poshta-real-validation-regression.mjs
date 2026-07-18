import fs from "node:fs";

const read = (path) => fs.readFileSync(path, "utf8");
const root = process.cwd();
const file = (path) => read(`${root}/${path}`);

const service = file("backend/app/services/nova_poshta_service.py");
const operation = file("backend/app/models/nova_poshta_operation.py");
const migration = file("backend/alembic/versions/202607150022_nova_poshta_durable_operations.py");
const api = file("backend/app/api/v1/shipments.py");
const client = file("backend/app/integrations/nova_poshta_client.py");
const button = file("frontend/src/features/integrations/components/create-ttn-button.tsx");
const details = file("frontend/src/features/shipments/components/shipment-details.tsx");
const panel = file("frontend/src/features/integrations/components/nova-poshta-shipment-panel.tsx");
const integrationApi = file("backend/app/api/v1/nova_poshta.py");
const integrationService = file("frontend/src/services/integrations.ts");
const settingsCard = file("frontend/src/features/integrations/components/nova-poshta-settings-card.tsx");
const fulfillmentWizard = file("frontend/src/features/orders/components/order-fulfillment-wizard.tsx");

const checks = [
  ["provider writes default disabled", /staging_nova_poshta_allow_writes/.test(service)],
  ["no process-local duplicate set", !/_in_progress_ttn_keys/.test(service)],
  ["durable unique shipment operation", /uq_nova_poshta_operations_workspace_shipment_type/.test(operation + migration)],
  ["durable calling state committed before provider call", /CALLING_PROVIDER/.test(service) && /self\.db\.commit\(\)[\s\S]*create_internet_document/.test(service)],
  ["ambiguous response blocks blind retry", /RECONCILIATION_REQUIRED/.test(service) && /blind_retry_blocked=True/.test(service)],
  ["provider reconciliation exists", /find_internet_document/.test(client + service) && /reconcile_ttn/.test(service)],
  ["reconcile API is workspace scoped and manager protected", /reconcile-ttn/.test(api) && /require_min_role\(RoleName\.MANAGER\)/.test(api)],
  ["unknown status preserves normalized state", /previous_normalized_status/.test(service) && /manual_review_required=normalized_status is None/.test(service)],
  ["frontend synchronous submit lock", /createInFlight\.current/.test(button) && /onSettled/.test(button)],
  ["manual reconciliation UI exists", /data-nova-poshta-manual-reconciliation/.test(button) && /reconcileNovaPoshtaTtn/.test(button)],
  ["provider refs are not primary raw UI labels", /shipment\.nova_poshta_city_ref \? t\("common\.yes"\)/.test(panel)],
  ["provider cancellation is not exposed", /status === "CANCELLED" && hasProviderDocument/.test(details)],
  ["readiness API is manager-readable", /\/readiness/.test(integrationApi) && /require_min_role\(RoleName\.MANAGER\)/.test(integrationApi)],
  ["readiness response excludes credential and sender refs", /NovaPoshtaReadinessResponse/.test(integrationApi) && !/class NovaPoshtaReadinessResponse[\s\S]*masked_api_key/.test(file("backend/app/schemas/integration.py"))],
  ["owner can explicitly activate provider writes", /updateNovaPoshtaWritePermission/.test(integrationService) && /onUpdateWritePermission/.test(settingsCard)],
  ["order wizard uses safe readiness instead of owner settings", /fetchNovaPoshtaReadiness/.test(fulfillmentWizard) && !/fetchNovaPoshtaSettings/.test(fulfillmentWizard)],
];

const failed = checks.filter(([, ok]) => !ok).map(([name]) => name);
for (const [name, ok] of checks) console.log(`${ok ? "PASS" : "FAIL"}: ${name}`);
if (failed.length) {
  console.error(`Sprint 8E regression failed: ${failed.join(", ")}`);
  process.exit(1);
}
console.log(`Sprint 8E static regression: ${checks.length}/${checks.length} PASS`);
