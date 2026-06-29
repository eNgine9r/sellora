import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const read = (path) => readFileSync(join(root, path), "utf8");
const exists = (path) => existsSync(join(root, path));
const checks = [];
const expect = (name, condition) => checks.push({ name, condition });

const csv = read("docs/templates/advertising-import-template.csv");
const importGuide = read("docs/advertising-import-guide.md");
const stagingQa = read("docs/advertising-staging-qa.md");
const pilotGuide = read("docs/pilot-advertising-guide.md");
const metricsDoc = read("docs/advertising-metrics.md");
const metaPlan = read("docs/meta-ads-integration-plan.md");
const privacyDoc = read("docs/meta-ads-privacy-safety.md");
const stagingChecklist = read("docs/staging-qa-checklist.md");
const pilotChecklist = read("docs/pilot-qa-checklist.md");
const readiness = read("docs/mvp-readiness.md");
const limitations = read("docs/known-limitations.md");
const advertisingPage = read("frontend/src/app/advertising/page.tsx");
const importPage = read("frontend/src/app/settings/import/page.tsx");
const uk = read("frontend/src/i18n/messages/uk.json");
const en = read("frontend/src/i18n/messages/en.json");
const combined = [csv, importGuide, stagingQa, pilotGuide, metricsDoc, metaPlan, privacyDoc, stagingChecklist, pilotChecklist, readiness, limitations, advertisingPage, importPage, uk, en].join("\n");

expect("advertising CSV template exists", exists("docs/templates/advertising-import-template.csv") && exists("frontend/public/templates/advertising-import-template.csv"));
expect("template uses Ukrainian-first supported columns", csv.startsWith("Дата,Кампанія,Платформа,Витрати,Повідомлення,Ліди,Замовлення,Дохід,Чистий прибуток,Покази,Кліки"));
expect("template has required synthetic demo rows", csv.includes("DEMO Meta Campaign — Watches") && csv.includes("DEMO Instagram Campaign — Rings") && csv.includes("DEMO Retargeting Campaign"));
expect("template includes zero-denominator edge row", csv.includes("DEMO Zero Leads Campaign") && csv.includes(",0,0,0,0,"));
expect("advertising import guide exists with bilingual privacy warning", importGuide.includes("Не завантажуйте реальні експорти") && importGuide.includes("Do not upload real ad account exports"));
expect("staging QA guide includes 22-step flow markers", stagingQa.includes("1. Open `/settings/import`.") && stagingQa.includes("22. Confirm dark/light themes are readable."));
expect("pilot advertising guide explains ROAS/CPA/CPL simply", pilotGuide.includes("ROAS 5 означає") && pilotGuide.includes("CPA 200 грн") && pilotGuide.includes("CPL 50 грн"));
expect("/advertising links to CSV template and Import Center", advertisingPage.includes("/templates/advertising-import-template.csv") && advertisingPage.includes("/settings/import"));
expect("/settings/import advertising preset explains template and next action", importPage.includes("importCenter.templateTitle") && importPage.includes("importCenter.requiredColumns") && importPage.includes("/advertising"));
expect("manual/import source and formula explanations remain in i18n", uk.includes("Імпортуйте рекламні метрики") && en.includes("Import advertising metrics first") && combined.includes("Manual/import"));
expect("dashboard/analytics consistency docs are present", stagingQa.includes("Dashboard") && stagingQa.includes("Analytics") && metricsDoc.includes("Sprint 4.2 Pilot Template Dataset"));
expect("optional attribution and Meta future-work markers remain", pilotGuide.includes("campaign_id") && metaPlan.includes("do not activate OAuth") && readiness.includes("Meta Ads API automation remains future work"));
expect("privacy/safety docs prohibit sensitive ad data", privacyDoc.includes("must not be replaced with a real ad account export") && combined.includes("tokens") && combined.includes("business IDs"));
expect("no raw token/secret/account fixture is introduced", !/EA[A-Za-z0-9]{20,}|app_secret\s*[:=]\s*['\"][^'\"]+|act_\d{6,}|\b\d{15,18}\b/.test(combined));

const failed = checks.filter((check) => !check.condition);
if (failed.length) {
  console.error("Advertising staging pilot readiness regression failed:");
  for (const check of failed) console.error(`- ${check.name}`);
  process.exit(1);
}

console.log(`Advertising staging pilot readiness regression passed (${checks.length} checks).`);
