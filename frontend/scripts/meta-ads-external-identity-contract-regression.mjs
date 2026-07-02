import fs from "node:fs";

const read = (path) => fs.readFileSync(path, "utf8");
const exists = (path) => fs.existsSync(path);
const checks = [];
const expect = (name, condition) => checks.push({ name, passed: Boolean(condition) });

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
const codePaths = [
  "backend/app/integrations/meta_ads/repository.py",
  "backend/app/integrations/meta_ads/preview_service.py",
  "backend/app/integrations/meta_ads/schemas.py",
];

for (const path of docsPaths) expect(`${path} exists`, exists(path));
for (const path of codePaths) expect(`${path} exists`, exists(path));

const docs = docsPaths.filter(exists).map(read).join("\n");
const code = codePaths.filter(exists).map(read).join("\n");
const combined = `${docs}\n${code}`;

expect("external_source design", combined.includes("external_source") && combined.includes("meta_ads"));
expect("external_account_id design", combined.includes("external_account_id"));
expect("external_campaign_id design", combined.includes("external_campaign_id"));
expect("source_type design", combined.includes("source_type") && combined.includes("manual") && combined.includes("csv_import") && combined.includes("meta_sync"));
expect("meta_sync_runs design", combined.includes("meta_sync_runs") && combined.includes("errors_count") && combined.includes("dry_run"));
expect("meta_ad_connections design", combined.includes("meta_ad_connections") && combined.includes("token_encrypted_ref"));
expect("nullable-first migration plan", combined.includes("Phase B") && combined.includes("nullable") && combined.includes("Phase F"));
expect("manual CSV backfill plan", combined.includes("backfill") && combined.includes("manual") && combined.includes("csv_import"));
expect("manual CSV protection", combined.includes("Manual/CSV data is protected") || combined.includes("manual/CSV rows are protected"));
expect("Meta-owned row update policy", combined.includes("Meta-owned rows") && combined.includes("same external identity"));
expect("no live Meta API", combined.includes("no live Meta API") && combined.includes("not active"));
expect("no token storage", combined.includes("Do not implement token storage in Sprint 4.9") || combined.includes("no token storage"));
expect("migration remains runtime-gated", combined.includes("runtime-gated") || combined.includes("does not create or apply an Alembic migration") || combined.includes("no database migration"));
expect("no DB writes", combined.includes("No DB writes are added for Meta sync") || combined.includes("no DB writes"));
expect("orders revenue profit remain Sellora-side", combined.includes("Orders, revenue, and net profit remain Sellora-side") || combined.includes("orders, revenue, and profit remain Sellora-side"));
expect("Sprint 4.4 blockers documented", combined.includes("Sprint 4.4") && combined.includes("PostgreSQL runtime"));
expect("advertising import not pilot-ready", combined.includes("advertising import remains not pilot-ready") || combined.includes("Advertising import remains not pilot-ready"));
expect("no sync-run persistence implemented", !/meta_sync_runs\s*=|class\s+MetaSyncRun|__tablename__\s*=\s*["']meta_sync_runs["']/.test(code));
expect("no live Meta HTTP calls", !/requests\.|httpx\.|urllib\.request|GraphAPI|facebook_business/.test(code));
expect("no token storage implementation", !/encrypted_token|access_token|refresh_token/.test(code));

const failed = checks.filter((check) => !check.passed);
if (failed.length) {
  console.error("Meta Ads external identity contract regression failed:");
  for (const check of failed) console.error(`- ${check.name}`);
  process.exit(1);
}

console.log(`Meta Ads external identity contract regression passed (${checks.length} checks).`);
