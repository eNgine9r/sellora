import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const read = (path) => readFileSync(join(root, path), "utf8");
const checks = [];
function assertMarker(path, marker, label = marker) {
  const source = read(path);
  if (!source.includes(marker)) {
    checks.push(`Missing ${label} in ${path}`);
  }
}
function assertNoMarker(path, marker, label = marker) {
  const source = read(path);
  if (source.includes(marker)) {
    checks.push(`Unexpected ${label} in ${path}`);
  }
}

const orderForm = "frontend/src/features/orders/components/order-form.tsx";
const ordersPage = "frontend/src/app/orders/page.tsx";
const orderDetails = "frontend/src/features/orders/components/order-details.tsx";
const shipmentForm = "frontend/src/features/shipments/components/shipment-form.tsx";
const payloadBuilders = "frontend/src/lib/payload-builders.ts";
const orderService = "backend/app/services/order_service.py";
const shipmentService = "backend/app/services/shipment_service.py";
const orderTests = "backend/tests/test_orders.py";
const shipmentTests = "backend/tests/test_shipments.py";
const ukMessages = "frontend/src/i18n/messages/uk.json";
const enMessages = "frontend/src/i18n/messages/en.json";

// Customer selector in order form with no raw UUID-first UX.
assertMarker(orderForm, "orders.customerSelector");
assertMarker(orderForm, "orders.customerSearchPlaceholder");
assertMarker(orderForm, "customerSearch");
assertMarker(orderForm, "customer.phone");
assertMarker(orderForm, "customer.instagram_username");
assertMarker(orderForm, "orders.customerOrdersCount");
assertNoMarker(orderForm, "Customer ID", "raw Customer ID primary UX");

// Quick create customer flow and required validation.
assertMarker(orderForm, "createQuickCustomer");
assertMarker(orderForm, "onCreateCustomer");
assertMarker(orderForm, "customers.quickCreate");
assertMarker(orderForm, "customers.quickCreateError");
assertMarker(orderForm, "orders.customerRequired");
assertMarker(ordersPage, "fetchCustomers(workspaceId)");
assertMarker(ordersPage, "createCustomerMutation");
assertMarker(ordersPage, "customer_name");
assertMarker(ordersPage, "customer_instagram_username");

// Order payload and detail display carry customer linkage.
assertMarker(payloadBuilders, "customer_id: cleanOptionalUuid(values.customer_id)");
assertMarker(orderDetails, "orders.customerSelector");
assertMarker(orderDetails, "order.customer_name");
assertMarker(orderDetails, "order.customer_phone");
assertMarker(orderDetails, "order.customer_instagram_username");
assertMarker(orderDetails, "shipments.orderCustomerMissing");

// Shipment creation is prefilled and blocked safely when order customer is missing.
assertMarker(shipmentForm, "selectedOrder.customer_name");
assertMarker(shipmentForm, "selectedOrder.customer_phone");
assertMarker(shipmentForm, "shipments.orderCustomerMissing");
assertMarker(shipmentForm, "customer_id: selectedOrder?.customer_id");

// Backend workspace-isolated customer validation and safe shipment guard.
assertMarker(orderService, "_get_order_customer");
assertMarker(orderService, "Customer is required to create an order");
assertMarker(orderService, "Customer not found in this workspace");
assertMarker(shipmentService, "order does not have a customer");
assertMarker(shipmentService, "Shipment customer must match the order customer");
assertMarker(orderTests, "test_order_creation_requires_customer_for_normal_orders");
assertMarker(orderTests, "test_order_creation_rejects_cross_workspace_customer_link");
assertMarker(orderTests, "test_order_response_exposes_linked_customer_fields");
assertMarker(shipmentTests, "test_shipment_creation_blocks_order_without_customer");
assertMarker(shipmentTests, "test_shipment_creation_rejects_customer_from_other_workspace");

// Required i18n keys exist in both locales.
[
  "orders.customerSelector",
  "orders.customerRequired",
  "orders.customerSearchPlaceholder",
  "orders.createCustomer",
  "orders.customerPreview",
  "orders.customerMissing",
  "shipments.orderCustomerMissing",
  "shipments.customerRequiredForShipment",
  "customers.quickCreate",
  "customers.quickCreateSuccess",
  "customers.quickCreateError",
].forEach((key) => {
  const [section, item] = key.split(".");
  assertMarker(ukMessages, `"${section}"`, `section ${section} in Ukrainian messages`);
  assertMarker(ukMessages, `"${item}"`, `key ${key} in Ukrainian messages`);
  assertMarker(enMessages, `"${section}"`, `section ${section} in English messages`);
  assertMarker(enMessages, `"${item}"`, `key ${key} in English messages`);
});

if (checks.length) {
  console.error("Order/customer linking regression failed:");
  for (const check of checks) console.error(`- ${check}`);
  process.exit(1);
}

console.log("Order/customer linking regression passed.");
