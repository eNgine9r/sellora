import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
const assertIncludes = (file, needle) => {
  const content = read(file);
  if (!content.includes(needle)) throw new Error(`${file} missing marker: ${needle}`);
};
const assertNotIncludes = (file, needle) => {
  const content = read(file);
  if (content.includes(needle)) throw new Error(`${file} contains forbidden marker: ${needle}`);
};

const files = {
  page: "frontend/src/app/advertising/page.tsx",
  panel: "frontend/src/features/advertising/components/campaign-insights-panel.tsx",
  rules: "frontend/src/features/advertising/lib/decision-support.ts",
  uk: "frontend/src/i18n/messages/uk.json",
  en: "frontend/src/i18n/messages/en.json",
  metrics: "docs/advertising-metrics.md",
  pilot: "docs/pilot-advertising-guide.md",
  readiness: "docs/mvp-readiness.md",
  limitations: "docs/known-limitations.md",
  staging: "docs/staging-qa-checklist.md",
  pilotQa: "docs/pilot-qa-checklist.md",
};

assertIncludes(files.page, "CampaignInsightsPanel");
assertIncludes(files.page, "campaigns={campaigns.data ?? []}");
assertIncludes(files.panel, "campaign-comparison-decision-support");
assertIncludes(files.panel, "data-decision-statuses=\"GOOD WATCH PROBLEM NO_DATA\"");
assertIncludes(files.panel, "noDataVisibilityHint");
assertIncludes(files.panel, "dark:bg-slate-950");
assertIncludes(files.panel, "overflow-x-auto");
assertIncludes(files.panel, "campaign.hasMetricData ? campaign.messages : DASH");
assertNotIncludes(files.panel, "NaN");
assertNotIncludes(files.panel, "Infinity");

for (const marker of [
  "GOOD",
  "WATCH",
  "PROBLEM",
  "NO_DATA",
  "mergeCampaignsWithPerformance",
  "emptyPerformanceRow",
  "hasMetricData: false",
  "decisionProblemLeadsNoOrders",
  "decisionWatchHighCpa",
  "decisionWatchWeakConversion",
  "Priority order: 1. NO_DATA, 2. PROBLEM, 3. GOOD, 4. WATCH",
  "roas != null && roas >= 4 && orders > 0 && revenue > 0",
  "safeDivide",
]) {
  assertIncludes(files.rules, marker);
}

for (const marker of ["Добре працює", "Потрібно спостерігати", "Потребує уваги", "Недостатньо даних", "Ліди є, але замовлень немає", "Недостатньо рекламних даних", "Advertising import не позначено pilot-ready"]) {
  assertIncludes(files.uk, marker);
}
for (const marker of ["Works well", "Watch closely", "Needs attention", "Not enough data", "Leads exist, but there are no orders", "Not enough advertising data", "not marked pilot-ready"]) {
  assertIncludes(files.en, marker);
}

for (const file of [files.metrics, files.pilot, files.readiness, files.limitations, files.staging, files.pilotQa]) {
  assertIncludes(file, "Sprint 4.3");
  assertIncludes(file, "Meta Ads");
}
assertIncludes(files.metrics, "NO_DATA → PROBLEM → GOOD → WATCH");
assertIncludes(files.metrics, "spend > 0, leads > 0, orders = 0");
assertIncludes(files.metrics, "Campaigns without metrics");
assertIncludes(files.metrics, "Top Campaigns");
assertIncludes(files.metrics, "Campaigns Needing Attention");
assertIncludes(files.pilot, "Недостатньо рекламних даних");
assertIncludes(files.readiness, "Advertising import remains blocked");
assertIncludes(files.limitations, "not pilot-ready");

for (const file of Object.values(files)) {
  assertNotIncludes(file, "EAAB");
  assertNotIncludes(file, "ad_account_id=");
  assertNotIncludes(file, "business_id=");
  assertNotIncludes(file, "app_secret=");
  assertNotIncludes(file, "password=");
}

console.log("advertising insights decision support regression passed");
