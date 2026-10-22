import { readFileSync } from "node:fs";

const read = (path) => readFileSync(path, "utf8");
const api = read("backend/app/services/customer_service.py");
const schema = read("backend/app/schemas/customer.py");
const route = read("backend/app/api/v1/customers.py");
const page = read("frontend/src/app/customers/page.tsx");
const cards = read("frontend/src/features/customers/components/customer-table.tsx");
const details = read("frontend/src/features/customers/components/customer-details.tsx");
const tests = read("backend/tests/test_customer_purchase_metrics.py");
const uk = JSON.parse(read("frontend/src/i18n/messages/uk.json"));
const en = JSON.parse(read("frontend/src/i18n/messages/en.json"));

const checks = [
  ["live customer metrics from scoped Orders not stale stored counters", api.includes("Order.workspace_id == workspace_id") && api.includes("Order.customer_id.in_(customer_ids)") && !api.includes("customer.total_orders +=")],
  ["paid-only totals do not count COD or pending", api.includes("payment_status == PaymentStatus.PAID.value") && api.includes("status not in (OrderStatus.CANCELLED.value, OrderStatus.RETURNED.value)")],
  ["last order is based on linked order record", api.includes('summary["last_order_at"] = created_at') && api.includes('summary["last_order_number"] = order_number')],
  ["unknown archival revenue tracked independently", api.includes('summary["unpriced_orders"] += 1')],
  ["customer order history endpoint protected by workspace and role", route.includes('router.get("/{customer_id}/orders"') && route.includes('Depends(require_min_role(RoleName.ANALYST))') && api.includes("Order.workspace_id == workspace_id")],
  ["selected customer fetches history lazily", page.includes('queryKey: ["customer-orders", workspaceId, selectedId]') && page.includes("enabled: enabled && Boolean(selectedId)")],
  ["workspace summary reports real counts", page.includes("customersWithPaidPurchases") && page.includes("repeatCustomers") && page.includes("customersWithoutOrders")],
  ["mobile cards have compact click-to-open UX", cards.includes("mobile-customer-card") && cards.includes("ChevronRight") && !cards.includes('onClick={(event) => { event.stopPropagation(); onEdit(customer); }')],
  ["large destructive actions not repeated on every mobile card", cards.includes('className="grid gap-2 md:hidden"') && !cards.includes("Архівувати клієнта")],
  ["details include Instagram Direct and linked products", details.includes("source_direct_conversation_id") && details.includes("order.products.map") && details.includes("shipment_tracking")],
  ["unattributed historical sales explicitly excluded", details.includes("unlinkedHistoryNotice")],
  ["new source labels translated", ["uk","en"].every((lang)=> (lang==="uk"?uk:en).customers.sources.INSTAGRAM_DIRECT)],
  ["unit tests cover paid, pending and returned", tests.includes("PaymentStatus.PENDING.value") && tests.includes("OrderStatus.RETURNED.value")],
  ["customer Pydantic fields support provenance", schema.includes("paid_orders: int") && schema.includes("unpriced_orders: int")],
];
const failed = checks.filter(([,passed])=>!passed);
for (const [label,passed] of checks) console.log(`${passed?"PASS":"FAIL"} ${label}`);
if (failed.length) process.exit(1);
