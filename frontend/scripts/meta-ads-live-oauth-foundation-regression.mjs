import fs from "node:fs";
import path from "node:path";

const read = (filePath) => fs.readFileSync(filePath, "utf8");
const checks = [];
const expect = (name, condition) => checks.push({ name, passed: Boolean(condition) });
const walk = (dir, predicate = () => true) => {
  const files = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (["node_modules", ".next", "__pycache__"].includes(entry.name)) continue;
      files.push(...walk(full, predicate));
    } else if (predicate(full)) files.push(full);
  }
  return files;
};

const config = read("backend/app/core/config.py");
const model = read("backend/app/models/meta_ad_connection.py");
const migration = read("backend/alembic/versions/202607030018_meta_ad_connections.py");
const crypto = read("backend/app/integrations/meta_ads/token_crypto.py");
const service = read("backend/app/services/meta_ads_connection_service.py");
const api = read("backend/app/api/v1/meta_ads.py");
const schemas = read("backend/app/schemas/meta_ads_connection.py");
const tests = [
  read("backend/tests/test_meta_ads_connections.py"),
  read("backend/tests/test_meta_ads_live_oauth_foundation.py"),
  read("backend/tests/test_meta_ads_token_crypto.py"),
].join("\n");
const docs = [
  "README.md",
  "docs/meta-api-part-6-readiness-plan.md",
  "docs/meta-token-storage-design.md",
  "docs/meta-connection-status-contract.md",
  "docs/meta-live-oauth-design.md",
  "docs/meta-api-staging-qa-checklist.md",
  "docs/known-limitations.md",
  "docs/mvp-readiness.md",
  "docs/advertising-known-blockers.md",
  "docs/meta-connection-records.md",
  "docs/meta-live-oauth-foundation.md",
].filter((file) => fs.existsSync(file)).map(read).join("\n");
const appCode = walk("backend/app", (file) => file.endsWith(".py")).map((file) => `${file}\n${read(file)}`).join("\n");

expect("feature gates disabled by default", config.includes('meta_live_oauth_enabled: bool = Field(default=False') && config.includes('meta_connections_enabled: bool = Field(default=False') && config.includes('meta_token_storage_enabled: bool = Field(default=False') && config.includes('meta_sync_enabled: bool = Field(default=False'));
expect("optional server-only Meta config placeholders", config.includes('meta_app_id: str | None') && config.includes('meta_app_secret: str | None') && config.includes('meta_token_encryption_key: str | None'));
expect("meta_ad_connections migration exists", migration.includes('op.create_table(\n        "meta_ad_connections"'));
expect("encrypted token storage utility exists", crypto.includes("Fernet") && crypto.includes("encrypt_token") && crypto.includes("decrypt_token"));
expect("no raw access_token column", model.includes("encrypted_access_token") && !/^\s*access_token:\s/m.test(model) && !migration.includes('sa.Column("access_token"'));
expect("no refresh token column", !/refresh_token/i.test(`${model}\n${migration}`));
expect("no token returned to frontend", !schemas.includes("encrypted_access_token") && !schemas.includes("access_token:"));
expect("OWNER-only connect/disconnect", api.includes('require_min_role(RoleName.OWNER)') && api.includes('/oauth/start') && api.includes('/disconnect'));
expect("MANAGER/ANALYST denial tests", tests.includes("RoleName.MANAGER") && tests.includes("RoleName.ANALYST") && tests.includes("status_code == 403"));
expect("status route safe", api.includes('/status') && api.includes('require_min_role(RoleName.ANALYST)') && tests.includes('"connection_status"'));
expect("callback state validation", service.includes("validate_live_oauth_state") && tests.includes("invalid state should fail"));
expect("no sync trigger", config.includes("meta_sync_enabled") && !/sync_started|schedule|background job|apply_sync/i.test(service));
expect("no Conversions API", !/Conversions API active|customer event upload|send.*customer.*Meta/i.test(appCode));
expect("no apply-sync", !/apply-sync|apply_sync/i.test(appCode));
expect("Meta API not sync-active", docs.includes("Meta Ads API is not sync-active."));
expect("Advertising not pilot-ready", docs.includes("Advertising remains feature-frozen and not pilot-ready."));
expect("required Sprint 6B wording", docs.includes("Sprint 6B adds encrypted token storage infrastructure and connection records behind feature gates."));
expect("real OAuth validation blockers documented", docs.includes("Real OAuth validation requires staging URLs, legal review, Meta App setup, and safe PostgreSQL runtime migration QA."));
expect("no real credentials", !/EA[A-Za-z0-9]{20,}|act_\d{8,}|Authorization: Bearer\s+[A-Za-z0-9._-]+/.test(`${appCode}\n${docs}\n${tests}`));
expect("no live Meta domains in backend integration modules", !/facebook\.com|graph\.facebook\.com/.test(walk("backend/app/integrations/meta_ads", (file) => file.endsWith(".py")).map(read).join("\n")));

const failed = checks.filter((check) => !check.passed);
if (failed.length) {
  console.error("Meta Ads live OAuth foundation regression failed:");
  for (const check of failed) console.error(`- ${check.name}`);
  process.exit(1);
}

console.log(`Meta Ads live OAuth foundation regression passed (${checks.length} checks).`);
