import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const read = (path) => readFileSync(join(root, path), "utf8");
const checks = [];
const expect = (name, condition) => checks.push({ name, condition });

const importService = read("backend/app/services/import_center_service.py");
const advertisingPage = read("frontend/src/app/advertising/page.tsx");
const campaignTable = read("frontend/src/features/advertising/components/campaign-table.tsx");
const uk = read("frontend/src/i18n/messages/uk.json");
const en = read("frontend/src/i18n/messages/en.json");
const metricsDoc = read("docs/advertising-metrics.md");
const metaPlan = read("docs/meta-ads-integration-plan.md");
const privacyDoc = read("docs/meta-ads-privacy-safety.md");
const stagingDoc = read("docs/staging-qa-checklist.md");
const pilotDoc = read("docs/pilot-qa-checklist.md");
const readinessDoc = read("docs/mvp-readiness.md");
const limitationsDoc = read("docs/known-limitations.md");
const combined = [importService, advertisingPage, campaignTable, uk, en, metricsDoc, metaPlan, privacyDoc, stagingDoc, pilotDoc, readinessDoc, limitationsDoc].join("\n");

expect("advertising import QA synthetic campaign is documented", metricsDoc.includes("DEMO Meta Campaign") && metricsDoc.includes("1000 UAH") && metricsDoc.includes("ROAS") && metricsDoc.includes("5.0"));
expect("synthetic campaign data only safety is documented", privacyDoc.includes("Synthetic QA Rule") && privacyDoc.includes("Do not commit real campaign exports"));
expect("Ukrainian/English column aliases include campaign/date/spend markers", importService.includes("Назва кампанії") && importService.includes("campaign_name") && importService.includes("Рекламний бюджет") && importService.includes("Чистий прибуток"));
expect("campaign source badge remains visible", campaignTable.includes("data-campaign-mapping-source=\"manual-import-meta-ready\"") && campaignTable.includes("advertising.manualSource"));
expect("manual/import source clarity appears on advertising page", advertisingPage.includes("advertising.manualImportFirst") && advertisingPage.includes("advertising.manualSource"));
expect("ROAS/CPA/CPL explanations are present in i18n", uk.includes("ROAS показує") && uk.includes("CPA показує") && uk.includes("CPL показує") && en.includes("ROAS shows") && en.includes("CPA shows") && en.includes("CPL shows"));
expect("zero denominator safe display is documented", metricsDoc.includes("Zero denominators") && metricsDoc.includes("NaN") && metricsDoc.includes("Infinity"));
expect("dashboard/analytics consistency is documented", metricsDoc.includes("Dashboard, Analytics") && readinessDoc.includes("Dashboard, Analytics, and `/advertising`"));
expect("campaign attribution optionality is documented and surfaced", metricsDoc.includes("Campaign attribution remains intentionally optional") && advertisingPage.includes("advertising.attributionOptional") && metaPlan.includes("Campaign selection must remain optional"));
expect("workspace/RBAC markers remain documented", pilotDoc.includes("Workspace/RBAC expectations") && combined.includes("workspace-scoped"));
expect("Meta API future-work marker remains present", readinessDoc.includes("Real Meta Ads API integration remains future work") && limitationsDoc.includes("Real Meta Ads API sync is not active"));
expect("privacy safety markers mention prohibited sensitive Meta data", combined.includes("real ad account IDs") && combined.includes("Meta tokens") && combined.includes("business IDs"));
expect("i18n keys for reporting polish exist", uk.includes("importMetricsFirst") && uk.includes("filteredEmpty") && en.includes("importMetricsFirst") && en.includes("filteredEmpty"));
expect("no raw token/secret fixture markers are introduced", !/EA[A-Za-z0-9]{20,}|app_secret\s*[:=]\s*['\"][^'\"]+|act_\d{6,}/.test(combined));

const failed = checks.filter((check) => !check.condition);
if (failed.length) {
  console.error("Advertising import attribution reporting regression failed:");
  for (const check of failed) console.error(`- ${check.name}`);
  process.exit(1);
}

console.log(`Advertising import attribution reporting regression passed (${checks.length} checks).`);
