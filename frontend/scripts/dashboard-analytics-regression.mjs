import { readFileSync, existsSync } from "node:fs";
import assert from "node:assert/strict";

const read = (path) => readFileSync(path, "utf8");
const dashboard = read("frontend/src/app/dashboard/page.tsx");
const layout = read("frontend/src/app/layout.tsx");
const provider = read("frontend/src/providers/date-range-provider.tsx");
const presets = read("frontend/src/lib/date-range-presets.ts");
const topProducts = read("frontend/src/features/dashboard/components/top-products-card.tsx");
const recentOrders = read("frontend/src/features/dashboard/components/recent-orders-table.tsx");
const notifications = read("frontend/src/features/dashboard/components/notifications-card.tsx");
const activity = read("frontend/src/features/dashboard/components/activity-feed.tsx");
const en = read("frontend/src/i18n/messages/en.json");
const uk = read("frontend/src/i18n/messages/uk.json");

assert(existsSync("frontend/src/providers/date-range-provider.tsx") && layout.includes("<DateRangeProvider>") && dashboard.includes("useDateRange()"), "dashboard consumes shared date range state");
assert(provider.includes("previousDateRange") && presets.includes("previousDateRange") && dashboard.includes("previousSalesSummary"), "previous equivalent period comparison is wired");
assert(dashboard.includes("fetchSalesSummary") && dashboard.includes("fetchProfitSummary") && dashboard.includes("fetchSalesTrend") && dashboard.includes("fetchTopProducts"), "dashboard uses real analytics hooks");
assert(dashboard.includes("fetchAdvertisingSummary") && dashboard.includes("fetchInventorySummary") && dashboard.includes("fetchShipmentSummary"), "dashboard uses real advertising, inventory and shipment data hooks");
assert(dashboard.includes("fetchOrders") && dashboard.includes("fetchLeads") && dashboard.includes("currentOrders") && dashboard.includes("currentLeads"), "dashboard derives period order and lead metrics from real data");
assert(dashboard.includes("safeRatio") && dashboard.includes("deltaPercent") && !/[+][0-9]+%/.test(dashboard), "dashboard avoids fake static percentage markers and guards ratio math");
assert(dashboard.includes("canSeeProfit") && dashboard.includes("dashboard.restricted") && dashboard.includes("enabled: enabled && canSeeProfit"), "dashboard has role-aware profit/financial visibility markers");
assert(dashboard.includes("orderStatusData") && dashboard.includes("DASHBOARD_ORDER_STATUSES") && dashboard.includes("formatStatus(\"order\""), "order status funnel uses localized real status counts");
assert(topProducts.includes("TopProductView") && topProducts.includes("imageUrl") && topProducts.includes("quantity_sold") && topProducts.includes("dashboard.topProducts"), "top products block shows image/category/quantity/revenue markers");
assert(dashboard.includes("topCategories") && dashboard.includes("dashboard.topCategories") && dashboard.includes("displayCategory"), "top categories block derives localized categories");
assert(dashboard.includes("dashboard.advertising") && dashboard.includes("average_cpa") && dashboard.includes("average_cpl"), "advertising summary includes CPA/CPL markers");
assert(dashboard.includes("dashboard.inventoryAlerts") && dashboard.includes("low_stock_items") && dashboard.includes("dashboard.logistics"), "inventory alerts and logistics blocks are present");
assert(recentOrders.includes("payment_status") && recentOrders.includes("showProfit") && recentOrders.includes("formatStatus(\"payment\""), "recent orders show payment status and role-aware profit");
assert(notifications.includes("DashboardNotification") && activity.includes("DashboardActivity") && dashboard.includes("dashboard.notificationsItems") && dashboard.includes("dashboard.activityItems"), "notifications/activity feed use real operational events");
assert(dashboard.includes("LoadingSkeleton") && dashboard.includes("ErrorState") && dashboard.includes("EmptyState"), "dashboard separates loading, error and empty states");
for (const key of ["analytics", "kpis", "charts", "topProducts", "topCategories", "inventoryAlerts", "logistics", "advertising", "recentOrders", "activity", "tooltips", "emptyStates", "errors", "comparison"]) {
  assert(en.includes(`\"${key}\"`) && uk.includes(`\"${key}\"`), `dashboard ${key} i18n keys exist in both locales`);
}
assert(en.includes("ROAS shows") && uk.includes("ROAS показує"), "dashboard metric explanations are localized");
assert(dashboard.includes("formatMoney") && recentOrders.includes("formatMoney") && topProducts.includes("formatMoney"), "dashboard uses workspace currency formatting helpers");
console.log("dashboard analytics regression passed");
