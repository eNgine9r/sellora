import fs from "node:fs";

const read = (path) => fs.readFileSync(path, "utf8");
const exists = (path) => fs.existsSync(path);
const checks = [];
const expect = (name, condition) => checks.push({ name, passed: Boolean(condition) });

const files = {
  repository: "backend/app/integrations/meta_ads/repository.py",
  previewService: "backend/app/integrations/meta_ads/preview_service.py",
  schemas: "backend/app/integrations/meta_ads/schemas.py",
  previewTests: "backend/tests/test_meta_ads_sync_preview.py",
};
for (const [name, path] of Object.entries(files)) expect(`${name} exists`, exists(path));

const sources = Object.values(files).filter(exists).map(read).join("\n");
const docs = [
  "docs/meta-ads-integration-plan.md",
  "docs/meta-ads-technical-design.md",
  "docs/advertising-metrics.md",
  "docs/advertising-import-guide.md",
  "docs/known-limitations.md",
  "docs/mvp-readiness.md",
  "README.md",
].map(read).join("\n");
const combined = `${sources}\n${docs}`;

expect("read-only repository boundary", sources.includes("AdvertisingSyncReadRepository") && sources.includes("ExistingAdCampaignSnapshot") && sources.includes("ExistingAdMetricSnapshot") && !/def\s+(create|update|delete)\(/.test(read(files.repository)));
expect("sync preview service", sources.includes("MetaAdsSyncPreviewService") && sources.includes("preview_sync") && sources.includes("read_repository"));
expect("preview DTOs", sources.includes("MetaSyncPreviewResultDTO") && sources.includes("MetaCampaignPreviewItemDTO") && sources.includes("MetaMetricPreviewItemDTO") && sources.includes("MetaSyncPreviewSummaryDTO"));
expect("classification markers", ["WOULD_CREATE", "WOULD_UPDATE", "WOULD_SKIP", "POTENTIAL_CONFLICT", "NEEDS_EXTERNAL_ID_SUPPORT", "INVALID"].every((marker) => combined.includes(marker)));
expect("manual CSV conflict policy", combined.includes("Manual/CSV data is protected") && combined.includes("POTENTIAL_CONFLICT") && combined.includes("manual/CSV rows"));
expect("no live Meta API calls", !/requests\.|httpx\.|urllib\.request|GraphAPI|facebook_business/.test(sources));
expect("no token storage", !/encrypted_token|access_token|refresh_token/.test(sources));
expect("no DB writes", combined.includes("db_writes") && combined.includes("db_writes = false") && !/\.commit\(|\.flush\(|\.add\(/.test(sources));
expect("no database migration", docs.includes("no database migration") || docs.includes("no migration"));
expect("orders revenue profit remain Sellora-side", docs.includes("orders, revenue, and profit remain Sellora-side") || docs.includes("Orders, revenue, and net profit remain Sellora-side"));
expect("external ID limitation documented", combined.includes("external_source/external_id") && combined.includes("external Meta identity persistence is still future work"));
expect("manual CSV remains active source", docs.includes("manual entry and CSV import remain") && docs.includes("current MVP advertising data source"));
expect("advertising import not pilot-ready", docs.includes("Advertising import remains not pilot-ready") || docs.includes("advertising import remains not pilot-ready"));
expect("Sprint 4.4 runtime blocker documented", docs.includes("Sprint 4.4") && docs.includes("PostgreSQL runtime"));

const failed = checks.filter((check) => !check.passed);
if (failed.length) {
  console.error("Meta Ads sync preview regression failed:");
  for (const check of failed) console.error(`- ${check.name}`);
  process.exit(1);
}

console.log(`Meta Ads sync preview regression passed (${checks.length} checks).`);
