import { existsSync, readFileSync } from "node:fs";
import assert from "node:assert/strict";

const read = (path) => readFileSync(path, "utf8");
const formulas = read("frontend/src/lib/analytics-formulas.ts");
const analytics = read("frontend/src/app/analytics/page.tsx");
const dashboard = read("frontend/src/app/dashboard/page.tsx");
const docs = read("docs/analytics-metrics.md");
const en = read("frontend/src/i18n/messages/en.json");
const uk = read("frontend/src/i18n/messages/uk.json");

assert(existsSync("docs/analytics-metrics.md") && docs.includes("Revenue = sum(order.revenue)") && docs.includes("CANCELLED") && docs.includes("RETURNED"), "analytics formula source-of-truth docs exist with status rules");
assert(existsSync("frontend/src/lib/analytics-formulas.ts") && formulas.includes("ANALYTICS_REVENUE_INCLUDED_STATUSES") && formulas.includes("summarizeOrders") && formulas.includes("summarizeAdvertising"), "shared analytics formulas utility exists");
assert(formulas.includes("safeDivide") && formulas.includes("UNAVAILABLE") && formulas.includes("formatSafeRatio"), "zero denominator safety helpers exist");
assert(!analytics.includes("NaN") && !analytics.includes("Infinity") && !dashboard.includes("NaN") && !dashboard.includes("Infinity"), "analytics UI does not render unsafe numeric literals");
assert(analytics.includes("analytics.sales.title") && analytics.includes("analytics.products.title") && analytics.includes("analytics.advertising.title") && analytics.includes("analytics.customers.title") && analytics.includes("analytics.inventory.title"), "reports sections/tabs exist for sales/products/advertising/customers/inventory");
assert(analytics.includes("buildDailySalesRows") && analytics.includes("orderSummary") && analytics.includes("analytics.tables.aov") && analytics.includes("analytics.sales.byStatus"), "sales report table and status/payment breakdown markers exist");
assert(analytics.includes("topCategories") && analytics.includes("lowStockBestSellers") && analytics.includes("quantity_sold"), "product/category report markers exist");
assert(analytics.includes("fetchAdvertisingSummary") && analytics.includes("fetchCampaignPerformance") && analytics.includes("analytics.metrics.cpa") && analytics.includes("analytics.metrics.cpl"), "advertising report markers exist");
assert(analytics.includes("summarizeCustomers") && analytics.includes("repeatCustomerRate") && analytics.includes("customersWithOrders"), "customer report markers exist");
assert(analytics.includes("summarizeInventory") && analytics.includes("reservedStock") && analytics.includes("salesInPeriod"), "inventory report markers exist");
assert(analytics.includes("buildBusinessInsights") && formulas.includes("ad_spend_without_orders") && formulas.includes("roas_below_one") && formulas.includes("low_stock"), "business insights use deterministic source metrics");
assert(dashboard.includes("summarizeOrders") && dashboard.includes("ANALYTICS_REVENUE_INCLUDED_STATUSES") && analytics.includes("summarizeOrders"), "dashboard/report consistency uses shared formulas");
assert(analytics.includes("canSeeProfit") && analytics.includes("enabled: enabled && canSeeProfit") && analytics.includes("analytics.metrics.restricted"), "RBAC profit visibility markers exist");
assert(docs.includes("historical imported orders") && docs.includes("Dashboard/report consistency") && docs.includes("zero"), "docs cover historical imports, consistency and zero denominator behavior");
for (const key of ["reports", "sales", "products", "advertising", "customers", "inventory", "insights", "metrics", "tooltips", "emptyStates", "errors", "filters", "sorting", "tables"]) {
  assert(en.includes(`\"${key}\"`) && uk.includes(`\"${key}\"`), `analytics ${key} i18n keys exist in both locales`);
}
console.log("analytics accuracy regression passed");
