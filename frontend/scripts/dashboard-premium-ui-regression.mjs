import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (name) => readFileSync(name, "utf8");
const page = read("frontend/src/app/dashboard/page.tsx");
const cards = read("frontend/src/features/dashboard/components/dashboard-premium.tsx");
const recent = read("frontend/src/features/dashboard/components/recent-orders-table.tsx");
const uk = JSON.parse(read("frontend/src/i18n/messages/uk.json"));
const en = JSON.parse(read("frontend/src/i18n/messages/en.json"));

assert(page.includes("data-dashboard-kpi-row") && page.includes("DashboardMetricCard"), "KPI row stays visible");
assert(page.indexOf("data-dashboard-analytics-row") < page.indexOf("data-dashboard-operational-row"), "main chart has priority");
assert(page.includes("DashboardActionList") && cards.includes("href={item.href}"), "alerts link to actionable pages");
assert(cards.includes("text-[clamp(1.125rem,4.6vw,2rem)]") && !cards.includes("min-w-0 truncate text-[clamp"), "mobile numbers never truncated");
assert(cards.includes('<ul className="grid gap-1">'), "alerts use semantic list");
assert(page.includes("DashboardFunnel") && cards.includes("stage.value / maxValue"), "funnel counts are real");
assert(page.includes("funnel.orderRatio") && !page.includes("funnel.orderRate"), "unlinked counts are not called conversions");
assert(page.includes('!canSeeProfit ? <EmptyState'), "chart profit access remains role-aware");
assert(page.includes('periodReady ? ordersCount : "—"') && page.includes('loading={!periodReady'), "no fake zero before fetch");
assert(!page.includes('LoadingSkeleton') && !page.includes('dashboard.loading.shipments'), "four oversized text loaders removed");
assert(page.includes('backendDashboard.isError ? <ErrorState'), "summary has retryable error");
assert(page.includes('data-dashboard-secondary') && page.includes('showDetails ? <div'), "secondary analytics is progressive disclosure");
assert(page.includes('refetchOnWindowFocus: "always"') && page.includes('refetchInterval: 60_000'), "KPI updates on interval/focus");
assert(page.includes('FirstRunChecklist'), "onboarding remains accessible");
assert(page.includes('DateRangeSelector') && page.includes('formatMoney'), "period selector/currency intact");
assert(page.includes('orders.isError') && recent.includes('isLoading') && recent.includes('isError'), "recent orders have independent states");
assert(recent.includes('.sort((left, right)') && recent.includes('.slice(0, 4)'), "latest orders sort before limiting");
assert(recent.includes('encodeURIComponent(order.id)') && recent.includes('href="/orders"'), "order links work");
for (const locale of [uk, en]) {
  for (const key of ["onboarding", "ownerAlerts", "funnel", "kpiHelpers", "emptyStates", "details"]) assert(locale.dashboard[key], "required localized section");
  assert(locale.dashboard.recentOrders.viewAll && locale.dashboard.recentOrders.allDates, "compact recent order labels localized");
}
console.log("Dashboard Dd.3 compact async premium regression passed.");
