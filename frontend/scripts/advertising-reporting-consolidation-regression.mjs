import fs from "node:fs";

const read = (path) => fs.readFileSync(path, "utf8");
const checks = [];
const expect = (name, condition) => checks.push({ name, passed: Boolean(condition) });

const advertisingPage = read("frontend/src/app/advertising/page.tsx");
const uk = read("frontend/src/i18n/messages/uk.json");
const en = read("frontend/src/i18n/messages/en.json");
const metricsDoc = read("docs/advertising-metrics.md");
const knownLimitations = read("docs/known-limitations.md");
const readinessDoc = read("docs/mvp-readiness.md");
const decisionSupport = read("frontend/src/features/advertising/lib/decision-support.ts");
const insightsPanel = read("frontend/src/features/advertising/components/campaign-insights-panel.tsx");
const dashboardOverview = read("frontend/src/features/advertising/components/advertising-dashboard-overview.tsx");
const trendChart = read("frontend/src/features/advertising/components/advertising-trend-chart.tsx");
const performanceTable = read("frontend/src/features/advertising/components/campaign-performance-table.tsx");

expect("advertising dashboard has analytics views and retained editable data", advertisingPage.includes("data-advertising-overview-hero") && advertisingPage.includes("data-advertising-campaigns-view") && advertisingPage.includes("data-advertising-data-view") && advertisingPage.includes("CampaignPerformanceTable") && advertisingPage.includes("AdMetricTable"));
expect("connected Meta Ads has no future-only warning in main report", !advertisingPage.includes("advertising.futureMetaSync") && !advertisingPage.includes("advertising.manualImportFirst") && advertisingPage.includes("hasMetaMetrics") && advertisingPage.includes("adsDashboard.metaSource"));
expect("campaign insights remain progressive and attribution limitations clear", advertisingPage.includes("data-advertising-attribution-disclaimer") && dashboardOverview.includes("adsDashboard.noAttributionNotice") && uk.includes("не означає, що реклама не принесла замовлень у CRM") && en.includes("does not mean these campaigns generated no CRM orders"));
expect("QA readiness diagnostic removed from user-facing report", !advertisingPage.includes("data-advertising-readiness-gate") && advertisingPage.includes("data-advertising-connection-settings"));
expect("marketing spend remains distinct from CRM revenue", dashboardOverview.includes("hasAttributedRevenue") && dashboardOverview.includes("adsDashboard.revenueCaption") && trendChart.includes("adsDashboard.trendCaption") && !trendChart.includes('dataKey="roas"'));
expect("campaign performance emphasizes ads messages and attributable CRM orders", performanceTable.includes("adsDashboard.costPerMessage") && performanceTable.includes("adsDashboard.crmLabel"));
expect("formula docs cover attribution and zero-denominator safety", metricsDoc.includes("Attributed Revenue") && metricsDoc.includes("Attributed Net Profit") && metricsDoc.includes("Cost per Message") && metricsDoc.includes("must not render `NaN`, `Infinity`, `undefined`, or raw `null`"));
expect("decision statuses remain UI-level labels", decisionSupport.includes('"GOOD" | "WATCH" | "PROBLEM" | "NO_DATA"') && insightsPanel.includes('data-decision-statuses="GOOD WATCH PROBLEM NO_DATA"'));
expect("decision priority remains documented in code", decisionSupport.includes("Priority order: 1. NO_DATA, 2. PROBLEM, 3. GOOD, 4. WATCH"));
expect("NO_DATA campaigns stay visible but out of top campaigns", decisionSupport.includes('.filter((row) => row.decision.status !== "NO_DATA")') && uk.includes("не потрапляють у найкращі кампанії"));
expect("advertising import is not falsely marked pilot-ready", knownLimitations.includes("Advertising import remains not pilot-ready") && readinessDoc.includes("advertising import is not pilot-ready") && !metricsDoc.includes("advertising import is pilot-ready"));
expect("Sprint 4.4 remains conditional until runtime/browser QA", metricsDoc.includes("Sprint 4.4 attribution is still not fully approved") && readinessDoc.includes("Sprint 4.4 PostgreSQL runtime/staging/browser QA blockers remain open"));
expect("privacy markers avoid credentials", !advertisingPage.includes("DATABASE_URL") && !advertisingPage.includes("access_token") && !metricsDoc.includes("Authorization: Bearer"));

const failed = checks.filter((check) => !check.passed);
if (failed.length) {
  console.error("Advertising reporting consolidation regression failed:");
  for (const check of failed) console.error(`- ${check.name}`);
  process.exit(1);
}

console.log(`Advertising reporting consolidation regression passed (${checks.length} checks).`);
