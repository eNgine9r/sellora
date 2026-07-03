import fs from "node:fs";

const read = (path) => fs.readFileSync(path, "utf8");
const exists = (path) => fs.existsSync(path);
const checks = [];
const expect = (name, condition) => checks.push({ name, passed: Boolean(condition) });

const paths = {
  config: "backend/app/core/config.py",
  router: "backend/app/api/v1/router.py",
  api: "backend/app/api/v1/meta_ads_mock.py",
  apiSchemas: "backend/app/schemas/meta_ads_mock.py",
  auditStub: "backend/app/integrations/meta_ads/audit_stub.py",
  oauthMock: "backend/app/integrations/meta_ads/oauth_mock.py",
  oauthState: "backend/app/integrations/meta_ads/oauth_state.py",
  tokenSafety: "backend/app/integrations/meta_ads/token_safety.py",
  routeTests: "backend/tests/test_meta_ads_oauth_mock_routes.py",
  frontendGates: "frontend/src/config/feature-gates.ts",
};
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

for (const path of [...Object.values(paths), ...docsPaths]) expect(`${path} exists`, exists(path));

const api = exists(paths.api) ? read(paths.api) : "";
const apiSchemas = exists(paths.apiSchemas) ? read(paths.apiSchemas) : "";
const config = exists(paths.config) ? read(paths.config) : "";
const router = exists(paths.router) ? read(paths.router) : "";
const auditStub = exists(paths.auditStub) ? read(paths.auditStub) : "";
const oauthMock = exists(paths.oauthMock) ? read(paths.oauthMock) : "";
const tokenSafety = exists(paths.tokenSafety) ? read(paths.tokenSafety) : "";
const tests = exists(paths.routeTests) ? read(paths.routeTests) : "";
const frontendGates = exists(paths.frontendGates) ? read(paths.frontendGates) : "";
const docs = docsPaths.filter(exists).map(read).join("\n");
const combined = `${api}\n${apiSchemas}\n${config}\n${router}\n${auditStub}\n${oauthMock}\n${tokenSafety}\n${tests}\n${docs}`;

expect("mock route prefix", api.includes('prefix="/integrations/meta-ads/mock"'));
expect("mock API feature gate disabled by default", config.includes("META_ADS_MOCK_OAUTH_API_ENABLED") && config.includes("default=False"));
expect("router includes mock API", router.includes("meta_ads_mock_router") && router.includes("include_router(meta_ads_mock_router)"));
expect("OWNER-only route-level contract", api.includes("require_min_role(RoleName.OWNER)") && api.includes("require_meta_ads_mock_owner"));
expect("MANAGER denied", tests.includes("RoleName.MANAGER") && tests.includes("status_code == 403"));
expect("ANALYST denied", tests.includes("RoleName.ANALYST") && tests.includes("status_code == 403"));
expect("status route marker", api.includes('@router.get("/status"'));
expect("start route marker", api.includes('@router.post("/oauth/start"'));
expect("callback route marker", api.includes('@router.post("/oauth/callback"'));
expect("disconnect route marker", api.includes('@router.post("/disconnect"'));
expect("mock Meta URL only", oauthMock.includes("https://mock.meta.local/oauth/authorize"));
expect("no facebook.com", !/facebook\.com/.test(api + oauthMock));
expect("no graph.facebook.com", !/graph\.facebook\.com/.test(api + oauthMock));
expect("no real OAuth URL", !/business\.facebook\.com|www\.facebook\.com|graph\.facebook\.com/.test(api + oauthMock));
expect("no token input", !/access_token|client_secret|refresh_token/.test(apiSchemas));
expect("no token storage", combined.includes("token_stored") && !/encrypted_access_token|store_token|save_token/.test(api + apiSchemas + auditStub));
expect("no meta_ad_connections table", !/create_table\(["']meta_ad_connections/.test(combined));
expect("no database migration", !/revision = .*mock_oauth|op\.create_table\(["']meta_ad_connections/.test(combined));
expect("no DB writes", !/\.commit\(|\.flush\(|\.add\(/.test(api + auditStub));
expect("no apply-sync", !/apply_sync|apply-sync|production sync trigger/.test(api + apiSchemas));
expect("audit event stubs", auditStub.includes("MetaAdsMockAuditEventDTO") && auditStub.includes("persisted: bool = False"));
expect("manual CSV active source", docs.includes("manual entry / CSV import"));
expect("Meta API not active", docs.includes("Meta Ads API inactive") || docs.includes("Meta sync remains not active"));
expect("Sprint 4.12 conditional documented", docs.includes("Sprint 4.12") && docs.includes("conditionally approved"));
expect("Sprint 4.10 runtime blocker documented", docs.includes("Sprint 4.10 runtime PostgreSQL migration QA remains pending"));
expect("Sprint 4.4 blockers documented", docs.includes("Sprint 4.4 PostgreSQL runtime/staging/browser QA blockers"));
expect("advertising import not pilot-ready", docs.includes("advertising import is not pilot-ready"));
expect("frontend OAuth remains gated", frontendGates.includes("metaAdsMockOAuthEnabled") && frontendGates.includes("false"));
expect("route tests prove no live domains", tests.includes("facebook.com") && tests.includes("graph.facebook.com"));

const failed = checks.filter((check) => !check.passed);
if (failed.length) {
  console.error("Meta Ads OAuth mock API boundary regression failed:");
  for (const check of failed) console.error(`- ${check.name}`);
  process.exit(1);
}

console.log(`Meta Ads OAuth mock API boundary regression passed (${checks.length} checks).`);
