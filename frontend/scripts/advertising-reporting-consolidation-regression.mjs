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

expect("advertising reporting structure markers exist", advertisingPage.includes("data-advertising-reporting-source") && advertisingPage.includes("CampaignInsightsPanel") && advertisingPage.includes("CampaignPerformanceTable") && advertisingPage.includes("AdMetricTable"));
expect("manual/import source messaging is visible", advertisingPage.includes("advertising.manualImportFirst") && advertisingPage.includes("advertising.manualSource") && uk.includes("ручний імпорт") && en.includes("manual import"));
expect("manual attribution messaging is visible", advertisingPage.includes("data-manual-attribution-summary") && advertisingPage.includes("advertising.manualAttributionLinkedOnly") && uk.includes("Атрибуція є ручною") && en.includes("Attribution is manual"));
expect("pilot readiness gate is present and not production-ready", advertisingPage.includes("data-advertising-readiness-gate") && uk.includes("не означає production-ready") && en.includes("does not mean production-ready"));
expect("Meta Ads API is clearly future work", uk.includes("майбутній етап, зараз не активний") && en.includes("future stage, not active now") && metricsDoc.includes("Meta Ads API remains future work"));
expect("formula docs cover attribution and zero-denominator safety", metricsDoc.includes("Attributed Revenue") && metricsDoc.includes("Attributed Net Profit") && metricsDoc.includes("Cost per Message") && metricsDoc.includes("must not render `NaN`, `Infinity`, `undefined`, or raw `null`"));
expect("decision statuses remain UI-level labels", decisionSupport.includes('"GOOD" | "WATCH" | "PROBLEM" | "NO_DATA"') && insightsPanel.includes('data-decision-statuses="GOOD WATCH PROBLEM NO_DATA"'));
expect("decision priority remains documented in code", decisionSupport.includes("Priority order: 1. NO_DATA, 2. PROBLEM, 3. GOOD, 4. WATCH"));
expect("NO_DATA campaigns stay visible but out of top campaigns", decisionSupport.includes('.filter((row) => row.decision.status !== "NO_DATA")') && uk.includes("не потрапляють у найкращі кампанії"));
expect("advertising import is not falsely marked pilot-ready", knownLimitations.includes("Advertising import remains not pilot-ready") && readinessDoc.includes("advertising import is not pilot-ready") && !metricsDoc.includes("advertising import is pilot-ready"));
expect("Sprint 4.4 remains conditional until runtime/browser QA", metricsDoc.includes("Sprint 4.4 attribution is still not fully approved") && readinessDoc.includes("Sprint 4.4 must not be marked fully approved"));
expect("privacy markers avoid credentials", !advertisingPage.includes("DATABASE_URL") && !advertisingPage.includes("access_token") && !metricsDoc.includes("Authorization: Bearer"));

const failed = checks.filter((check) => !check.passed);
if (failed.length) {
  console.error("Advertising reporting consolidation regression failed:");
  for (const check of failed) console.error(`- ${check.name}`);
  process.exit(1);
}

console.log(`Advertising reporting consolidation regression passed (${checks.length} checks).`);
