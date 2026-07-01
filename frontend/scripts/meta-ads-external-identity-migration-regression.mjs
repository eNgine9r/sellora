import fs from "node:fs";

const read = (path) => fs.readFileSync(path, "utf8");
const exists = (path) => fs.existsSync(path);
const checks = [];
const expect = (name, condition) => checks.push({ name, passed: Boolean(condition) });

const migrationPath = "backend/alembic/versions/202607010016_meta_ads_external_identity_fields.py";
const modelPaths = ["backend/app/models/ad_campaign.py", "backend/app/models/ad_metric.py"];
const previewPaths = ["backend/app/integrations/meta_ads/repository.py", "backend/app/integrations/meta_ads/preview_service.py"];
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

expect("migration draft exists", exists(migrationPath));
for (const path of [...modelPaths, ...previewPaths, ...docsPaths]) expect(`${path} exists`, exists(path));

const migration = exists(migrationPath) ? read(migrationPath) : "";
const models = modelPaths.filter(exists).map(read).join("\n");
const preview = previewPaths.filter(exists).map(read).join("\n");
const docs = docsPaths.filter(exists).map(read).join("\n");
const combined = `${migration}\n${models}\n${preview}\n${docs}`;

expect("external_source field", combined.includes("external_source"));
expect("external_account_id field", combined.includes("external_account_id"));
expect("external_campaign_id field", combined.includes("external_campaign_id"));
expect("source_type and sync_source fields", combined.includes("source_type") && combined.includes("sync_source"));
expect("nullable-first policy", migration.includes("nullable=True") && !migration.includes("nullable=False") && !migration.includes("server_default"));
expect("downgrade support", migration.includes("def downgrade") && migration.includes("drop_index") && migration.includes("drop_column"));
expect("campaign external identity index", migration.includes("ix_ad_campaigns_workspace_external_identity") && migration.includes("unique=False"));
expect("metric external identity date index", migration.includes("ix_ad_metrics_workspace_external_identity_date") && migration.includes("metric_date"));
expect("no token storage", !/access_token|refresh_token|token_encrypted_ref|encrypted_token/.test(migration + models));
expect("no live OAuth table", !/oauth|meta_ad_connections/.test(migration));
expect("no live Meta API calls", !/requests\.|httpx\.|urllib\.request|GraphAPI|facebook_business/.test(preview + models));
expect("no DB sync writes", docs.includes("no DB writes") && !/\.commit\(|\.flush\(|\.add\(/.test(preview));
expect("manual CSV protection", docs.includes("Manual/CSV") && docs.includes("protected"));
expect("external identity matching priority", preview.includes("external_identity_key") && docs.includes("exact external identity") && docs.includes("safe normalized name/platform fallback"));
expect("runtime-gated migration policy", docs.includes("runtime-gated") && docs.includes("safe non-production database"));
expect("advertising import not pilot-ready", docs.includes("advertising import remains not pilot-ready") || docs.includes("Advertising import remains not pilot-ready"));
expect("Sprint 4.4 runtime blocker documented", docs.includes("Sprint 4.4") && docs.includes("PostgreSQL runtime"));
expect("no persisted decision enums", !/GOOD|WATCH|PROBLEM|NO_DATA/.test(migration));

const failed = checks.filter((check) => !check.passed);
if (failed.length) {
  console.error("Meta Ads external identity migration regression failed:");
  for (const check of failed) console.error(`- ${check.name}`);
  process.exit(1);
}

console.log(`Meta Ads external identity migration regression passed (${checks.length} checks).`);
