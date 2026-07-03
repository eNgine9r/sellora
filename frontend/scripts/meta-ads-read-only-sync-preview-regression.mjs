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
const api = read("backend/app/api/v1/meta_ads.py");
const client = read("backend/app/integrations/meta_ads/read_only_client.py");
const schemas = read("backend/app/schemas/meta_ads_read_only.py");
const service = read("backend/app/services/meta_ads_sync_preview_service.py");
const tests = [
  read("backend/tests/test_meta_ads_read_only_discovery.py"),
  read("backend/tests/test_meta_ads_sync_preview_foundation.py"),
].join("\n");
const docs = [
  "README.md",
  "docs/meta-api-part-6-readiness-plan.md",
  "docs/meta-live-oauth-foundation.md",
  "docs/meta-connection-records.md",
  "docs/meta-api-staging-qa-checklist.md",
  "docs/known-limitations.md",
  "docs/mvp-readiness.md",
  "docs/advertising-known-blockers.md",
  "docs/meta-read-only-discovery.md",
  "docs/meta-sync-preview-foundation.md",
].map(read).join("\n");
const appCode = walk("backend/app", (file) => file.endsWith(".py")).map((file) => `${file}\n${read(file)}`).join("\n");

expect("feature gates disabled by default", config.includes('meta_sync_preview_enabled: bool = Field(default=False') && config.includes('meta_sync_enabled: bool = Field(default=False'));
expect("read-only discovery routes", api.includes('/discovery/accounts') && api.includes('/discovery/campaigns') && api.includes('/sync/preview'));
expect("account preview DTOs", schemas.includes("MetaAdAccountPreviewDTO") && schemas.includes("external_account_id_masked"));
expect("campaign preview DTOs", schemas.includes("MetaCampaignDiscoveryPreviewDTO") && schemas.includes("external_campaign_id_masked"));
expect("insights preview DTOs", schemas.includes("MetaInsightsPreviewDTO") && schemas.includes("spend") && schemas.includes("messages"));
expect("read-only client has no write methods", client.includes("MetaAdsReadOnlyClientProtocol") && !/create_campaign|update_campaign|delete_campaign|upload_customer/i.test(client));
expect("safe not-ready response", schemas.includes("MetaReadOnlyNotReadyResponse") && service.includes("feature_disabled") && service.includes("connection_not_ready"));
expect("no DB writes to ad_metrics", service.includes("No ad_campaigns or ad_metrics rows are written") && !/AdMetric\(|\.add\(|commit\(/.test(service));
expect("no DB writes to ad_campaigns", !/AdCampaign\(|create_campaign|update_campaign/.test(service));
expect("no apply-sync", !/apply-sync|apply_sync|applySync/i.test(appCode));
expect("no scheduled sync", !/schedule|cron|background job|BackgroundTasks/i.test(service));
expect("no Conversions API", !/Conversions API active|customer event upload|send.*customer.*Meta/i.test(appCode));
expect("no customer data sent to Meta", !/customer_id|order_id|customer payload|order payload/i.test(client + service));
expect("no raw token returned", !schemas.includes("encrypted_access_token") && !schemas.includes("access_token:"));
expect("Meta API not sync-active", docs.includes("Meta Ads API is not sync-active."));
expect("Advertising not pilot-ready", docs.includes("Advertising remains feature-frozen and not pilot-ready."));
expect("Manual CSV active source", docs.includes("Manual/CSV remains the active Advertising source."));
expect("backend tests cover no writes and masking", tests.includes("WriteTrapDb") && tests.includes("not in response.model_dump_json") && tests.includes("not in accounts.model_dump_json"));
expect("no real credentials", !/EA[A-Za-z0-9]{20,}|act_\d{8,}|Authorization: Bearer\s+[A-Za-z0-9._-]+/.test(`${appCode}\n${docs}\n${tests}`));
expect("no live Meta domains in read-only modules", !/facebook\.com|graph\.facebook\.com/.test(client + service));

const failed = checks.filter((check) => !check.passed);
if (failed.length) {
  console.error("Meta Ads read-only sync preview regression failed:");
  for (const check of failed) console.error(`- ${check.name}`);
  process.exit(1);
}

console.log(`Meta Ads read-only sync preview regression passed (${checks.length} checks).`);
