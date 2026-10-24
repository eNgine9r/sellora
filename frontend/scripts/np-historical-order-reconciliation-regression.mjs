import { readFileSync } from "node:fs";

const read = (path) => readFileSync(path, "utf8");
const form = read("frontend/src/features/orders/components/order-form.tsx");
const page = read("frontend/src/app/orders/page.tsx");
const details = read("frontend/src/features/orders/components/order-details.tsx");
const service = read("backend/app/services/order_service.py");
const provider = read("backend/app/services/nova_poshta_service.py");
const tracking = read("backend/app/services/nova_poshta_tracking.py");
const shipmentDetails = read("frontend/src/features/shipments/components/shipment-details.tsx");
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
  ["historic corrections unlock profit only after cost and price", details.includes("historicalValuesMissing") && details.includes("Number(order.revenue) <= 0") && details.includes("Number(order.product_cost) <= 0")],
  ["pending payment does not imply realized profit", details.includes("historicalUnpaidProfitHint")],
  ["unsynced historical orders are visibly unverified", details.includes("historicalStatusUnverified") && details.includes("!shipment.nova_poshta_synced_at")],
  ["unsynced imported shipments are visibly unverified", shipmentDetails.includes("providerUnverified") && shipmentDetails.includes('startsWith("NP-")')],
  ["shipments show declared value and carrier tariff without revenue inference", shipmentDetails.includes("shipment.declared_value") && shipmentDetails.includes("shipment.shipping_cost") && shipmentDetails.includes("providerValuesWarning")],
  ["carrier order status uses audited transitions without inferred payment", provider.includes("_update_order_for_tracking") && provider.includes("orders.change_status(") && provider.includes("never mark COD paid")],
  ["arrival mapping includes arrived/прибуло", tracking.includes('"7": ShipmentStatus.ARRIVED') && tracking.includes('"arrived"') && tracking.includes('"прибуло у відділення"')],
  ["English and Ukrainian labels exist", ["historicalCorrectionHint", "providerValuesWarning", "unknownAmount", "declaredValue", "carrierTariff"].every((key) => uk.orders[key] && en.orders[key])],
];
const failures = checks.filter(([, ok]) => !ok);
for (const [name, ok] of checks) console.log(`${ok ? "PASS" : "FAIL"} ${name}`);
if (failures.length) process.exit(1);
