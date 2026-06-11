import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const files = {
  globals: "frontend/src/app/globals.css",
  statusStyles: "frontend/src/lib/status-styles.ts",
  topbar: "frontend/src/components/app-topbar.tsx",
  themeToggle: "frontend/src/components/theme-toggle.tsx",
  inventoryTable: "frontend/src/features/inventory/components/inventory-table.tsx",
  orderTable: "frontend/src/features/orders/components/order-table.tsx",
  customerTable: "frontend/src/features/customers/components/customer-table.tsx",
  productTable: "frontend/src/features/products/components/product-table.tsx",
  shipmentBadge: "frontend/src/features/shipments/components/shipment-status-badge.tsx",
  leadBadge: "frontend/src/features/leads/components/lead-status-badge.tsx",
  importBadge: "frontend/src/features/import-center/components/import-job-status-badge.tsx",
  campaignTable: "frontend/src/features/advertising/components/campaign-table.tsx",
  adFilter: "frontend/src/features/advertising/components/advertising-date-range-filter.tsx",
  adCampaignForm: "frontend/src/features/advertising/components/campaign-form.tsx",
  adMetricForm: "frontend/src/features/advertising/components/ad-metric-form.tsx",
};

const source = Object.fromEntries(Object.entries(files).map(([key, path]) => [key, readFileSync(path, "utf8")]));

assert.match(source.statusStyles, /dark:border-emerald-400\/30/, "Shared status styles must include dark success contrast");
assert.match(source.statusStyles, /dark:bg-rose-400\/15/, "Shared status styles must include dark danger contrast");
assert.match(source.globals, /sellora-status-badge/, "Global status badge utility must exist");
assert.match(source.inventoryTable, /statusBadgeClass\("danger"\)/, "Inventory low stock badge must use shared high-contrast status style");
assert.match(source.inventoryTable, /statusBadgeClass\("success"\)/, "Inventory healthy badge must use shared high-contrast status style");
assert.match(source.orderTable, /StatusPill/, "Orders table must render status/payment badges");
assert.match(source.shipmentBadge, /statusBadgeClass/, "Shipment statuses must use shared badge styles");
assert.match(source.leadBadge, /statusBadgeClass/, "Lead statuses must use shared badge styles");
assert.match(source.importBadge, /statusBadgeClass/, "Import statuses must use shared badge styles");
assert.match(source.campaignTable, /statusBadgeClass/, "Advertising campaign statuses must use shared badge styles");
assert.match(source.productTable, /statusBadgeClass/, "Product active/inactive statuses must use shared badge styles");

assert.match(source.topbar, /flex-wrap items-center/, "Topbar must be able to reflow at zoom/constrained widths");
assert.match(source.topbar, /lg:flex-nowrap/, "Topbar should remain single-row on large layouts when possible");
assert.match(source.topbar, /min-w-\[220px\] flex-1/, "Topbar search must keep a usable flexible width");
assert.match(source.topbar, /h-12 w-40 shrink-0/, "Topbar date range select must have stable shrink-safe width");
assert.match(source.topbar, /whitespace-nowrap/, "Create/logout controls must not wrap awkwardly");
assert.match(source.topbar, /account-topbar-group/, "User/workspace and logout must be visually grouped");
assert.match(source.themeToggle, /shrink-0/, "Theme button must remain aligned as a fixed-size control");

assert.match(source.customerTable, /sellora-scrollbar/, "Customers table must use Sellora scrollbar styling");
assert.match(source.orderTable, /sellora-scrollbar/, "Orders table must use Sellora scrollbar styling");
assert.match(source.customerTable, /max-w-\[230px\] flex-wrap/, "Customer actions must wrap within a constrained cell");
assert.match(source.orderTable, /max-w-\[220px\] flex-wrap/, "Order actions must wrap within a constrained cell");
assert.match(source.globals, /\.sellora-scrollbar/, "Global app scrollbar utility must exist");
assert.match(source.globals, /dark \.sellora-scrollbar|dark \.sellora-scrollbar::-webkit-scrollbar-thumb/, "Scrollbar styling must include dark mode variants");

for (const [name, text] of Object.entries({ adFilter: source.adFilter, adCampaignForm: source.adCampaignForm, adMetricForm: source.adMetricForm })) {
  assert.match(text, /sellora-date-input/, `${name} date controls must use mobile-safe date marker`);
  assert.match(text, /w-full min-w-0 max-w-full/, `${name} date controls must be width constrained`);
  assert.doesNotMatch(text, /min-w-\[(?:3|4|5|6)\d{2}px\]/, `${name} must not use oversized fixed date input widths`);
}

console.log("Topbar table advertising polish regression passed");
