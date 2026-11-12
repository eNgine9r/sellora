import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (path) => readFileSync(path, "utf8");
const dashboard = read("frontend/src/app/dashboard/page.tsx");
const recentOrders = read("frontend/src/features/dashboard/components/recent-orders-table.tsx");
const topProducts = read("frontend/src/features/dashboard/components/top-products-card.tsx");
const revenueChart = read("frontend/src/features/dashboard/components/sales-profit-chart.tsx");
const statusChart = read("frontend/src/features/dashboard/components/order-status-chart.tsx");
const layout = read("frontend/src/app/layout.tsx");
const provider = read("frontend/src/providers/date-range-provider.tsx");
const presets = read("frontend/src/lib/date-range-presets.ts");
const en = JSON.parse(read("frontend/src/i18n/messages/en.json"));
const uk = JSON.parse(read("frontend/src/i18n/messages/uk.json"));

assert(layout.includes("<DateRangeProvider>") && dashboard.includes("useDateRange()"), "shared date range still powers dashboard");
assert(provider.includes("previousDateRange") && presets.includes("previousDateRange") && dashboard.includes("previousBackendDashboard"), "equivalent-period comparison preserved");
assert(dashboard.includes('fetchDashboardSummary') && dashboard.includes('["dashboard-backend-summary", workspaceId, dateFrom, dateTo]'), "period source is authoritative");
for (const oldCall of ["fetchSalesSummary", "fetchProfitSummary", "fetchSalesTrend", "fetchTopProducts", "fetchAdvertisingSummary", "fetchInventorySummary", "fetchProducts"]) {
  assert(!dashboard.includes(oldCall), oldCall + " duplicates an existing report, no longer needed");
}
assert(dashboard.includes("sales.daily_rows") && dashboard.includes("sales.order_status_breakdown"), "period chart and status pie use same snapshot");
assert(dashboard.includes("fetchOrders") && dashboard.includes("fetchLeads") && dashboard.includes("currentLeads"), "operational lists use real order/lead sources");
assert(dashboard.includes("enabled: enabled && periodReady") && dashboard.includes("enabled: enabled && periodReady && showDetails"), "noncritical fetches defer until necessary");
assert(dashboard.includes("formatSafeRatio") && dashboard.includes("formatDeltaPercent"), "ratio comparisons use safe math");
assert(dashboard.includes('rawProfit') && dashboard.includes('!canSeeProfit ? t("dashboard.restricted")'), "profit remains permission-gated");
assert(dashboard.includes("ANALYTICS_ORDER_STATUSES") && dashboard.includes('formatStatus("order"'), "status labels localized");
assert(dashboard.includes("DashboardFunnel") && dashboard.includes("funnel.orderRatio"), "funnel semantics preserved");
assert(topProducts.includes("imageUrl") && topProducts.includes("quantity_sold") && topProducts.includes("formatMoney"), "product cards retain factual data");
assert(recentOrders.includes("showProfit") && recentOrders.includes("formatMoney") && recentOrders.includes('StatusBadge'), "latest list preserves role-aware financial data and status");
assert(dashboard.includes('dynamic(') && dashboard.includes('showDetails ? <div') && revenueChart.includes("ResponsiveContainer") && statusChart.includes("ResponsiveContainer"), "large Recharts bundle is lazy");
assert(!dashboard.includes('from "recharts"'), "Recharts not bundled in main dashboard page");
assert(dashboard.includes('backendDashboard.isError ? <ErrorState') && dashboard.includes("EmptyState"), "independent pending/error/empty handling");
for (const locale of [uk,en]) {
  assert(locale.dashboard.details.title && locale.dashboard.recentOrders.allDates && locale.dashboard.recentOrders.viewAll, "new dashboard labels localized");
  assert(locale.dashboard.funnel.orderRatio && locale.dashboard.emptyStates.noRecordedFinancials, "formula caveats localized");
}
console.log("Dashboard analytics compact/performance regression passed.");
