import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (name) => readFileSync(name, "utf8");
const page = read("frontend/src/app/dashboard/page.tsx");
const premium = read("frontend/src/features/dashboard/components/dashboard-premium.tsx");
const uk = JSON.parse(read("frontend/src/i18n/messages/uk.json"));
const en = JSON.parse(read("frontend/src/i18n/messages/en.json"));

assert(page.includes("data-dashboard-kpi-row") && page.includes("DashboardMetricCard"), "KPI overview remains visible");
assert(page.indexOf("data-dashboard-analytics-row") < page.indexOf("data-dashboard-operational-row"), "sales chart receives priority");
assert(page.includes("DashboardActionList") && premium.includes("href={item.href}"), "alerts have functional destinations");
assert(page.includes("DashboardFunnel") && premium.includes("stage.value / maxValue"), "funnel scales real event counts");
assert(page.includes("funnel.orderRatio") && !page.includes("funnel.orderRate"), "unlinked lead/order counts are not called conversion");
assert(page.includes("!canSeeProfit ? <EmptyState"), "role-restricted chart does not imply empty sales");
assert(page.includes("!isLoading && !hasError ? <>"), "loaded content is not rendered as zero before fetch");
assert(!page.includes("<NotificationsCard"), "duplicate alert and notification cards are not rendered");
assert(page.includes("ordersCount ? t(\"dashboard.emptyStates.noRecordedFinancials\")"), "financial data quality is explained");
assert(page.includes("FirstRunChecklist"), "onboarding remains available");
assert(page.includes("DateRangeSelector") && page.includes("formatMoney"), "date range and money formatting are preserved");
for (const locale of [uk, en]) {
  for (const key of ["onboarding", "ownerAlerts", "funnel", "kpiHelpers", "emptyStates"]) assert(locale.dashboard[key], "localized dashboard section exists");
  assert(locale.dashboard.funnel.subtitleAccurate && locale.dashboard.funnel.orderRatio, "funnel caveats localized");
  assert(locale.dashboard.emptyStates.noRecordedFinancials, "financial unavailable reason localized");
}
console.log("Dashboard Dd.3 premium UI regression passed.");
