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
};

assertIncludes(files.page, "CampaignInsightsPanel");
assertIncludes(files.panel, "campaign-comparison-decision-support");
assertIncludes(files.panel, "data-decision-statuses=\"GOOD WATCH PROBLEM NO_DATA\"");
assertIncludes(files.panel, "topCampaigns");
assertIncludes(files.panel, "campaignsNeedingAttention");
assertIncludes(files.panel, "roasShortExplanation");
assertIncludes(files.panel, "costPerMessageShortExplanation");

for (const marker of ["GOOD", "WATCH", "PROBLEM", "NO_DATA", "decisionProblemSpendNoOrders", "decisionWatchHighCpa", "safeDivide"]) {
  assertIncludes(files.rules, marker);
}

for (const marker of ["Добре працює", "Потрібно спостерігати", "Потребує уваги", "Недостатньо даних", "Advertising import не позначено pilot-ready"]) {
  assertIncludes(files.uk, marker);
}
for (const marker of ["Works well", "Watch closely", "Needs attention", "Not enough data", "not marked pilot-ready"]) {
  assertIncludes(files.en, marker);
}

for (const file of [files.metrics, files.pilot, files.readiness, files.limitations]) {
  assertIncludes(file, "Sprint 4.3");
  assertIncludes(file, "Meta Ads");
}
assertIncludes(files.metrics, "Top Campaigns");
assertIncludes(files.metrics, "Campaigns Needing Attention");
assertIncludes(files.metrics, "NaN");
assertIncludes(files.pilot, "ручних або CSV-імпортованих");
assertIncludes(files.readiness, "Advertising import remains blocked");
assertIncludes(files.limitations, "not pilot-ready");

for (const file of Object.values(files)) {
  assertNotIncludes(file, "EAAB");
  assertNotIncludes(file, "ad_account_id=");
  assertNotIncludes(file, "business_id=");
  assertNotIncludes(file, "app_secret=");
}

console.log("advertising insights decision support regression passed");
