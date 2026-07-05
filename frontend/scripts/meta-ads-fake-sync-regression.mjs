import fs from "node:fs";

const read = (path) => fs.readFileSync(path, "utf8");
const exists = (path) => fs.existsSync(path);
const checks = [];
const expect = (name, condition) => checks.push({ name, passed: Boolean(condition) });

const files = {
  init: "backend/app/integrations/meta_ads/__init__.py",
  schemas: "backend/app/integrations/meta_ads/schemas.py",
  client: "backend/app/integrations/meta_ads/client.py",
  fakeClient: "backend/app/integrations/meta_ads/fake_client.py",
  mapper: "backend/app/integrations/meta_ads/mapper.py",
  syncService: "backend/app/integrations/meta_ads/sync_service.py",
  fakeTests: "backend/tests/test_meta_ads_fake_client.py",
  syncTests: "backend/tests/test_meta_ads_sync_simulation.py",
};

for (const [name, path] of Object.entries(files)) {
  expect(`${name} exists`, exists(path));
}

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

expect("client interface exists", sources.includes("class MetaAdsClientProtocol") && sources.includes("list_ad_accounts") && sources.includes("get_campaign_insights"));
expect("DTO contracts exist", sources.includes("MetaAdAccountDTO") && sources.includes("MetaCampaignDTO") && sources.includes("MetaInsightsRowDTO") && sources.includes("MetaSyncResultDTO"));
expect("fake client deterministic synthetic IDs", sources.includes("FakeMetaAdsClient") && sources.includes("fake_act_001") && sources.includes("fake_campaign_001"));
expect("mapping layer exists", sources.includes("map_campaign_to_candidate") && sources.includes("map_insights_to_metric_candidate") && sources.includes("AdMetricSyncCandidate"));
expect("dry-run sync simulation exists", sources.includes("MetaAdsDryRunSyncService") && sources.includes("simulate_sync") && sources.includes("dry_run"));
expect("no live Meta HTTP calls", !/requests\.|httpx\.|urllib\.request|GraphAPI|facebook_business/.test(sources));
expect("no real token/account fixtures", !/EA[A-Za-z0-9]{20,}|act_\d{8,}|Authorization: Bearer\s+[A-Za-z0-9._-]+/.test(combined));
expect("no token storage implementation", !/encrypted_token|access_token|refresh_token/.test(sources));
expect("manual CSV remains active source", docs.includes("manual entry and CSV import remain") && docs.includes("current MVP advertising data source"));
expect("Meta API remains not active", docs.includes("fake-client / simulation-ready / not active"));
expect("orders revenue profit remain Sellora-side", docs.includes("orders, revenue, and profit remain Sellora-side") || docs.includes("Orders, revenue, and net profit remain Sellora-side"));
expect("Conversions API separate future phase", docs.includes("Conversions API") && docs.includes("legally/privacy reviewed"));
expect("idempotency contract documented", docs.includes("workspace_id + external_source + external_campaign_id + metric_date"));
expect("advertising import not pilot-ready", docs.includes("Advertising import remains not pilot-ready") || docs.includes("advertising import remains not pilot-ready"));
expect("Sprint 4.4 runtime blocker documented", docs.includes("Sprint 4.4") && docs.includes("PostgreSQL runtime"));

const failed = checks.filter((check) => !check.passed);
if (failed.length) {
  console.error("Meta Ads fake sync regression failed:");
  for (const check of failed) console.error(`- ${check.name}`);
  process.exit(1);
}

console.log(`Meta Ads fake sync regression passed (${checks.length} checks).`);
