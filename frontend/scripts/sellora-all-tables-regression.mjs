import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const read = (p) => readFileSync(path.join(root, p), "utf8");
const shared = read("frontend/src/components/ui/responsive-report-table.tsx");
const css = read("frontend/src/app/globals.css");
assert(shared.includes("sellora-adaptive-list"), "Shared report component must track available container width");
assert(shared.includes("sellora-adaptive-table") && shared.includes("sellora-adaptive-cards"),
  "Shared report component must render both accessible table and labeled mobile cards");
assert(shared.includes("<th") && shared.includes("<dt") && shared.includes("<dd"),
  "Card metrics must have readable metric labels and values");
assert(shared.includes("rowKey"), "Row identity must remain stable");
assert(css.includes("@container (min-width: 780px)") && css.includes("@container (min-width: 980px)"),
  "Adaptive breakpoints must remain consistent with CRM lists");

const reportFiles = [
  "frontend/src/features/analytics/components/low-stock-table.tsx",
  "frontend/src/features/analytics/components/top-products-table.tsx",
  "frontend/src/features/analytics/components/top-customers-table.tsx",
  "frontend/src/features/import-center/components/import-logs-table.tsx",
  "frontend/src/features/import-center/components/import-preview-table.tsx",
  "frontend/src/features/import-center/components/validation-issues-table.tsx",
  "frontend/src/features/advertising/components/campaign-performance-table.tsx",
  "frontend/src/features/advertising/components/campaign-insights-panel.tsx",
  "frontend/src/app/analytics/page.tsx",
  "frontend/src/app/products/page.tsx",
];
for (const p of reportFiles) {
  const source = read(p);
  assert(source.includes("<ResponsiveReportTable"), `Missing shared table/card layout: ${p}`);
  assert(!source.includes("min-w-[920px]") && !source.includes("min-w-[980px]"),
    `Wide minimums introduce nested horizontal scrolling: ${p}`);
  assert(!source.includes("<table"), `Legacy raw table still exists outside shared report component: ${p}`);
}
const analytics = read("frontend/src/app/analytics/page.tsx");
assert.equal((analytics.match(/<ResponsiveReportTable/g) ?? []).length, 5,
  "All five analytics reports must support adaptive tables and cards");
assert(analytics.includes("...(canSeeProfit ? ["),
  "Analytics must continue to omit profit-sensitive columns based on workspace access");
const campaign = read("frontend/src/features/advertising/components/campaign-insights-panel.tsx");
assert(campaign.includes("CampaignDecisionBadge") && campaign.includes("conversionRateValue"),
  "Ads insight decision and conversion metrics must remain available");
const product = read("frontend/src/app/products/page.tsx");
assert(product.includes("RowActionButtons") && product.includes("setArchivingVariant(variant)") &&
  product.includes("setEditingVariant(variant)"), "Variant confirmations and editing must be preserved");
const team = read("frontend/src/app/settings/team/page.tsx");
assert(team.includes("sellora-adaptive-list") && team.includes("sellora-adaptive-cards") &&
  team.includes("RowActionButtons"), "Team list must have consistent actions and cards");
assert(team.includes("!lastOwner && !current") && team.includes("canManage"),
  "Protect current users and last owner from accidental deactivation");
const dashboard = read("frontend/src/features/dashboard/components/recent-orders-table.tsx");
assert(dashboard.includes("sellora-adaptive-list") &&
  dashboard.includes("sellora-adaptive-table") &&
  dashboard.includes("sellora-adaptive-cards"), "Dashboard orders must adapt to available width");

const operational = [
  "leads/components/lead-table.tsx",
  "orders/components/order-table.tsx",
  "customers/components/customer-table.tsx",
  "products/components/product-table.tsx",
  "shipments/components/shipment-table.tsx",
  "inventory/components/inventory-table.tsx",
  "advertising/components/campaign-table.tsx",
  "advertising/components/ad-metric-table.tsx",
];
for (const rel of operational) {
  const source = read(`frontend/src/features/${rel}`);
  assert(source.includes("sellora-adaptive-list"), `Operational layout regression: ${rel}`);
}
console.log("Sellora all-table consistency regression passed: 8 operational + 12 secondary surfaces.");
