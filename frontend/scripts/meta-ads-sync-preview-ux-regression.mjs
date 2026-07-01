import fs from "node:fs";

const read = (path) => fs.readFileSync(path, "utf8");
const exists = (path) => fs.existsSync(path);
const checks = [];
const expect = (name, condition) => checks.push({ name, passed: Boolean(condition) });

const featureGatePath = "frontend/src/config/feature-gates.ts";
const metaCardPath = "frontend/src/features/integrations/components/meta-ads-readiness-card.tsx";
const advertisingPagePath = "frontend/src/app/advertising/page.tsx";
const integrationsPagePath = "frontend/src/app/settings/integrations/page.tsx";
const ukPath = "frontend/src/i18n/messages/uk.json";
const enPath = "frontend/src/i18n/messages/en.json";
const docsPaths = [
  "README.md",
  "docs/meta-ads-integration-plan.md",
  "docs/meta-ads-technical-design.md",
  "docs/advertising-metrics.md",
  "docs/advertising-import-guide.md",
  "docs/pilot-advertising-guide.md",
  "docs/staging-qa-checklist.md",
  "docs/pilot-qa-checklist.md",
  "docs/mvp-readiness.md",
  "docs/known-limitations.md",
];

for (const path of [featureGatePath, metaCardPath, advertisingPagePath, integrationsPagePath, ukPath, enPath, ...docsPaths]) {
  expect(`${path} exists`, exists(path));
}

const featureGate = exists(featureGatePath) ? read(featureGatePath) : "";
const metaCard = exists(metaCardPath) ? read(metaCardPath) : "";
const advertisingPage = exists(advertisingPagePath) ? read(advertisingPagePath) : "";
const integrationsPage = exists(integrationsPagePath) ? read(integrationsPagePath) : "";
const uk = exists(ukPath) ? read(ukPath) : "";
const en = exists(enPath) ? read(enPath) : "";
const docs = docsPaths.filter(exists).map(read).join("\n");
const ui = `${metaCard}\n${advertisingPage}\n${integrationsPage}\n${uk}\n${en}`;
const combined = `${ui}\n${docs}`;

expect("feature gate disabled by default", featureGate.includes("metaAdsSyncPreviewEnabled") && featureGate.includes("false"));
expect("Meta Ads API not active copy", uk.includes("Meta Ads API ще не активний") && en.includes("Meta Ads API is not active yet"));
expect("manual CSV current source copy", uk.includes("ручне внесення та CSV-імпорт") && en.includes("manual entry and CSV import"));
expect("disabled coming-soon CTA", metaCard.includes("disabled") && uk.includes("Підключити Meta Ads — скоро") && en.includes("Connect Meta Ads — coming soon"));
expect("coming soon help copy", uk.includes("Підключення Meta Ads буде доступне на наступному етапі") && en.includes("Meta Ads connection will be available in a future stage"));
expect("future preview labels localized", ["WOULD_CREATE", "WOULD_UPDATE", "WOULD_SKIP", "POTENTIAL_CONFLICT", "NEEDS_EXTERNAL_ID_SUPPORT", "INVALID"].every((value) => combined.includes(value)) && uk.includes("Буде створено") && en.includes("Will be created"));
expect("manual CSV protection copy", uk.includes("Sellora не перезаписує ручні або CSV-рекламні дані автоматично") && en.includes("Sellora does not automatically overwrite manual or CSV advertising data"));
expect("orders revenue profit Sellora-side", uk.includes("Замовлення, дохід і прибуток залишаються даними Sellora") && en.includes("Orders, revenue, and profit remain Sellora-side data"));
expect("advertising page shows status card", advertisingPage.includes("MetaAdsReadinessCard"));
expect("settings integrations shows status card", integrationsPage.includes("MetaAdsReadinessCard"));
expect("no live OAuth route or link", !/oauth|authorize|facebook\.com\/dialog|graph\.facebook\.com/i.test(ui));
expect("no token input", !/type=\"password\"|access_token|refresh_token|token_encrypted_ref|token input/i.test(metaCard + advertisingPage + integrationsPage));
expect("no apply-sync button", !/apply-sync|apply sync|застосувати синхронізацію/i.test(ui));
expect("no production sync trigger", !/startSync|runSync|executeSync|production sync trigger/i.test(ui));
expect("no pilot-ready claim", !/advertising import is pilot-ready|ready for pilot|готовий до пілоту/i.test(ui));
expect("Sprint 4.10 runtime-gated status documented", docs.includes("Sprint 4.10") && docs.includes("runtime PostgreSQL migration QA remains skipped/pending"));
expect("Sprint 4.4 blockers documented", docs.includes("Sprint 4.4") && docs.includes("PostgreSQL runtime migration QA"));
expect("future states documented", ["NOT_ACTIVE", "COMING_SOON", "PREVIEW_AVAILABLE", "CONNECTED", "SYNCING", "TOKEN_EXPIRED"].every((value) => docs.includes(value)));

const failed = checks.filter((check) => !check.passed);
if (failed.length) {
  console.error("Meta Ads sync preview UX regression failed:");
  for (const check of failed) console.error(`- ${check.name}`);
  process.exit(1);
}

console.log(`Meta Ads sync preview UX regression passed (${checks.length} checks).`);
