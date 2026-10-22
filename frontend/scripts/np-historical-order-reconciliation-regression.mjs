import { readFileSync } from "node:fs";

const read = (path) => readFileSync(path, "utf8");
const form = read("frontend/src/features/orders/components/order-form.tsx");
const page = read("frontend/src/app/orders/page.tsx");
const details = read("frontend/src/features/orders/components/order-details.tsx");
const service = read("backend/app/services/order_service.py");
const provider = read("backend/app/services/nova_poshta_service.py");
const uk = JSON.parse(read("frontend/src/i18n/messages/uk.json"));
const en = JSON.parse(read("frontend/src/i18n/messages/en.json"));

const checks = [
  ["historical correction does not touch inventory", service.includes("if historical:") && service.includes('"affect_inventory": False') && service.includes("if order.is_historical:")],
  ["historical items remain editable after shipment", page.includes("lockedItems={!editingOrder.is_historical")],
  ["historical price not overwritten by current catalog price", form.includes('unit_price: initialOrder?.is_historical ? ""')],
  ["historical edit bypasses current stock availability", form.includes("!initialOrder?.is_historical &&")],
  ["archived placeholder still selectable", form.includes("історична позиція")],
  ["NP order sync action available", page.includes("syncNovaPoshtaStatus(workspaceId, shipmentId)") && details.includes("onSyncShipment")],
  ["provider tracking shown in order panel", details.includes("nova_poshta_raw_status") && details.includes("nova_poshta_synced_at")],
  ["carrier tariff and declared value distinct", details.includes("shipment.shipping_cost") && details.includes("shipment.declared_value")],
  ["historic unknown sale values are not zero", details.includes("archivePlaceholder") && details.includes('t("orders.unknownAmount")')],
  ["historical provider order status audited", provider.includes("NOVA_HISTORICAL_ORDER_STATUS_REVIEW_REQUIRED") && provider.includes("_sync_historical_order_status")],
  ["arrival mapping includes arrived/прибув", provider.includes('"прибув"')],
  ["English and Ukrainian labels exist", ["historicalCorrectionHint", "providerValuesWarning", "unknownAmount", "declaredValue", "carrierTariff"].every((key) => uk.orders[key] && en.orders[key])],
];
const failures = checks.filter(([, ok]) => !ok);
for (const [name, ok] of checks) console.log(`${ok ? "PASS" : "FAIL"} ${name}`);
if (failures.length) process.exit(1);
