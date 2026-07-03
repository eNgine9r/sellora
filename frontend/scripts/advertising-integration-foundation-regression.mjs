import { readFileSync, existsSync } from "node:fs";

const checks = [];
const read = (path) => readFileSync(path, "utf8");
const assertIncludes = (path, marker, label = marker) => {
  const content = read(path);
  if (!content.includes(marker)) {
    throw new Error(`${path} is missing ${label}`);
  }
  checks.push(`${path}: ${label}`);
};
const assertExists = (path) => {
  if (!existsSync(path)) throw new Error(`${path} does not exist`);
  checks.push(`${path}: exists`);
};

assertExists("docs/advertising-metrics.md");
assertExists("docs/meta-ads-integration-plan.md");
assertExists("docs/meta-ads-privacy-safety.md");

for (const marker of [
  "`revenue / ad_spend`",
  "`ad_spend / orders`",
  "`ad_spend / leads`",
  "Cost per Message",
  "NaN",
  "Manual import compatibility",
]) assertIncludes("docs/advertising-metrics.md", marker);

for (const marker of [
  "Automatic Meta Ads API sync is not active",
  "official Meta OAuth",
  "external_campaign_id",
  "workspace isolation",
  "manual fallback",
]) assertIncludes("docs/meta-ads-integration-plan.md", marker);

for (const marker of [
  "Never expose raw Meta access tokens",
  "Use official Meta APIs only",
  "Do not scrape Instagram Direct",
  "fake/mocked Meta clients",
]) assertIncludes("docs/meta-ads-privacy-safety.md", marker);

for (const marker of [
  "data-meta-ads-placeholder=\"manual-import-first\"",
  "metaAds.notActiveTitle",
  "metaAds.manualCsvProtection",
  "metaAds.connectComingSoon",
]) assertIncludes("frontend/src/features/integrations/components/meta-ads-readiness-card.tsx", marker);

for (const marker of [
  "MetaAdsReadinessCard",
  "NovaPoshtaSettingsCard",
]) assertIncludes("frontend/src/app/settings/integrations/page.tsx", marker);

for (const marker of [
  "advertising.manualImportFirst",
  "advertising.futureMetaSync",
  "advertising.formulaSafety",
]) assertIncludes("frontend/src/app/advertising/page.tsx", marker);

for (const marker of [
  "data-campaign-mapping-source=\"manual-import-meta-ready\"",
  "advertising.source",
  "advertising.manualSource",
  "Meta-ready mapping",
]) assertIncludes("frontend/src/features/advertising/components/campaign-table.tsx", marker);

for (const path of ["frontend/src/i18n/messages/uk.json", "frontend/src/i18n/messages/en.json"]) {
  for (const marker of [
    "metaAds",
    "manualImportSupported",
    "automaticLater",
    "manualImportFirst",
    "futureMetaSync",
    "formulaSafety",
  ]) assertIncludes(path, marker);
}

for (const marker of [
  "Sprint 4.0 — Advertising integration foundation",
  "OWNER-only credential-management",
  "workspace_id",
]) assertIncludes("docs/staging-qa-checklist.md", marker);

for (const marker of [
  "Sprint 4.0 — Advertising and Meta Ads readiness",
  "manual entry/import",
  "real Meta access token",
]) assertIncludes("docs/pilot-qa-checklist.md", marker);

for (const marker of [
  "Sprint 4.0 readiness — Advertising integration foundation",
  "automatic sync is future work",
]) assertIncludes("docs/mvp-readiness.md", marker);

for (const marker of [
  "Sprint 4.0 — Advertising and Meta Ads limitations",
  "Automatic Meta Ads OAuth",
]) assertIncludes("docs/known-limitations.md", marker);

const unsafeFixturePattern = /(EA[A-Z0-9]{20,}|app_secret\s*[:=]\s*[A-Za-z0-9]{12,}|act_\d{6,}|business_id\s*[:=]\s*\d{6,})/;
const scanned = [
  "docs/advertising-metrics.md",
  "docs/meta-ads-integration-plan.md",
  "docs/meta-ads-privacy-safety.md",
  "frontend/src/features/integrations/components/meta-ads-readiness-card.tsx",
  "frontend/src/app/advertising/page.tsx",
  "frontend/src/features/advertising/components/campaign-table.tsx",
].map((path) => `${path}\n${read(path)}`).join("\n");
if (unsafeFixturePattern.test(scanned)) {
  throw new Error("Potential raw Meta token/secret/account fixture found in Sprint 4.0 sources");
}

console.log(`Advertising integration foundation regression passed (${checks.length} markers).`);
