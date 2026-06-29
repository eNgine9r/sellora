import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const read = (path) => readFileSync(join(root, path), "utf8");
const failures = [];
function has(path, marker, label = marker) {
  if (!read(path).includes(marker)) failures.push(`Missing ${label} in ${path}`);
}

const shipmentsPage = "frontend/src/app/shipments/page.tsx";
const shipmentTable = "frontend/src/features/shipments/components/shipment-table.tsx";
const shipmentDetails = "frontend/src/features/shipments/components/shipment-details.tsx";
const ttnActions = "frontend/src/features/shipments/components/ttn-actions.tsx";
const npPanel = "frontend/src/features/integrations/components/nova-poshta-shipment-panel.tsx";
const ttnButton = "frontend/src/features/integrations/components/create-ttn-button.tsx";
const orderDetails = "frontend/src/features/orders/components/order-details.tsx";
const shipmentRepo = "backend/app/repositories/shipment_repository.py";
const shipmentService = "backend/app/services/shipment_service.py";
const shipmentTests = "backend/tests/test_shipments.py";
const uk = "frontend/src/i18n/messages/uk.json";
const en = "frontend/src/i18n/messages/en.json";

// Shipment list search/filter/pagination/action markers.
has(shipmentsPage, "shipments-pagination-section");
has(shipmentsPage, "PAGE_SIZE_OPTIONS");
has(shipmentsPage, "ttnFilter");
has(shipmentsPage, "missingTtn");
has(shipmentsPage, "needsAction");
has(shipmentsPage, "updatedRecently");
has(shipmentTable, "CopyTtnButton");
has(shipmentTable, "shipments.openOrder");
has(shipmentTable, "shipments.createTtn");
has(shipmentTable, "customer_phone");

// Shipment detail sections and TTN/document/status UX.
[
  "shipments.orderSection",
  "shipments.customerSection",
  "shipments.recipientSection",
  "shipments.trackingSection",
  "shipments.statusSection",
  "NovaPoshtaShipmentPanel",
  "TtnDocumentLimitation",
  "nova_poshta_raw_status",
  "nova_poshta_synced_at",
].forEach((marker) => has(shipmentDetails, marker));
has(ttnActions, "navigator.clipboard.writeText");
has(ttnActions, "shipments.ttnPrintUnavailable");
has(npPanel, "shipments.recipientAddressRequired");
has(npPanel, "shipments.ttnMissing");
has(ttnButton, "duplicateTtnWarning");
has(ttnButton, "senderSettingsRequired");
has(ttnButton, "statusSyncFailed");
has(ttnButton, "disabled={sync.isPending || !hasTtn}");

// Order detail shipment section markers.
has(orderDetails, "CopyTtnButton");
has(orderDetails, "shipments.createTtn");
has(orderDetails, "open shipment create TTN");

// Backend workspace/search/response safety markers.
has(shipmentRepo, "Shipment.order.has");
has(shipmentRepo, "Shipment.customer.has");
has(shipmentService, "order_status");
has(shipmentService, "customer_phone");
has(shipmentTests, "test_shipment_search_supports_context_source_markers");
has(shipmentTests, "customer_phone");

// i18n and docs markers.
[
  "copyTtn",
  "ttnCopied",
  "ttnPrintUnavailable",
  "statusUnavailable",
  "orderCustomerMissingUpdate",
  "duplicateTtnWarning",
  "pagination",
].forEach((key) => {
  has(uk, `"${key}"`, `Ukrainian ${key}`);
  has(en, `"${key}"`, `English ${key}`);
});
has("docs/shipment-workflow.md", "Printable/downloadable TTN documents");
has("docs/known-limitations.md", "Sprint 3.1");
has("docs/staging-qa-checklist.md", "Sprint 3.1");
has("docs/pilot-qa-checklist.md", "Sprint 3.1");
has("docs/mvp-readiness.md", "Sprint 3.1 readiness");

if (failures.length) {
  console.error("Shipment TTN documents/status regression failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}
console.log("Shipment TTN documents/status regression passed.");
