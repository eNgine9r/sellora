import fs from "node:fs";

const read = (path) => fs.readFileSync(path, "utf8");
const exists = (path) => fs.existsSync(path);
const checks = [];
const expect = (name, condition) => checks.push({ name, passed: Boolean(condition) });

const paths = {
  oauthMock: "backend/app/integrations/meta_ads/oauth_mock.py",
  oauthState: "backend/app/integrations/meta_ads/oauth_state.py",
  tokenSafety: "backend/app/integrations/meta_ads/token_safety.py",
  schemas: "backend/app/integrations/meta_ads/schemas.py",
  oauthTests: "backend/tests/test_meta_ads_oauth_mock.py",
  tokenTests: "backend/tests/test_meta_ads_token_safety.py",
  featureGates: "frontend/src/config/feature-gates.ts",
  metaCard: "frontend/src/features/integrations/components/meta-ads-readiness-card.tsx",
  uk: "frontend/src/i18n/messages/uk.json",
  en: "frontend/src/i18n/messages/en.json",
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

const source = Object.values(paths).filter(exists).map(read).join("\n");
const docs = docsPaths.filter(exists).map(read).join("\n");
const backend = [paths.oauthMock, paths.oauthState, paths.tokenSafety, paths.schemas].filter(exists).map(read).join("\n");
const tests = [paths.oauthTests, paths.tokenTests].filter(exists).map(read).join("\n");
const ui = [paths.featureGates, paths.metaCard, paths.uk, paths.en].filter(exists).map(read).join("\n");
const combined = `${source}\n${docs}`;

expect("mock OAuth only", combined.includes("mock OAuth") || combined.includes("Mock OAuth"));
expect("mock Meta URL", backend.includes("https://mock.meta.local/oauth/authorize"));
expect("OWNER-only contract", backend.includes("RoleName.OWNER") && docs.includes("OWNER may start"));
expect("MANAGER denied", tests.includes("RoleName.MANAGER") && docs.includes("MANAGER"));
expect("ANALYST denied", tests.includes("RoleName.ANALYST") && docs.includes("ANALYST"));
expect("state validation", backend.includes("validate_mock_oauth_state") && tests.includes("mismatched state") || tests.includes("mismatched_state") || tests.includes("mismatched"));
expect("token redaction", backend.includes("mask_token") && backend.includes("redact_secret_fields"));
expect("no raw token response", backend.includes("assert_no_raw_token_in_response") && tests.includes("raw_token_returned is False"));
expect("no token storage", combined.includes("token_stored = false") || combined.includes("token_stored=False"));
expect("no real Meta domain in mock backend", !/facebook\.com|graph\.facebook\.com|business\.facebook\.com/.test(backend));
expect("no live OAuth route", !/APIRouter|@router|oauth\/callback|oauth\/start/.test(backend));
expect("no live Meta API calls", !/requests\.|httpx\.|urllib\.request|facebook_business|GraphAPI/.test(backend));
expect("no DB writes", !/\.commit\(|\.flush\(|\.add\(/.test(backend));
expect("no apply-sync", !/apply_sync|apply-sync|production sync trigger/.test(backend + ui));
expect("manual CSV active source", docs.includes("manual entry / CSV import"));
expect("Meta API not active", docs.includes("Meta Ads API inactive") || docs.includes("Meta sync remains not active"));
expect("mock OAuth feature gate disabled", ui.includes("metaAdsMockOAuthEnabled") && ui.includes("false"));
expect("mock frontend copy", ui.includes("mock-flow") && ui.includes("no real Meta account is connected now"));
expect("Sprint 4.10 runtime blocker documented", docs.includes("Sprint 4.10 runtime PostgreSQL migration QA remains pending"));
expect("Sprint 4.4 blockers documented", docs.includes("Sprint 4.4 PostgreSQL runtime/staging/browser QA blockers"));
expect("advertising import not pilot-ready", docs.includes("advertising import is not pilot-ready"));
expect("no meta_ad_connections table", !/create_table\(["']meta_ad_connections/.test(combined));
expect("no database migration added marker", !/revision = .*meta_ad_connections/.test(combined));

const failed = checks.filter((check) => !check.passed);
if (failed.length) {
  console.error("Meta Ads OAuth mock safety regression failed:");
  for (const check of failed) console.error(`- ${check.name}`);
  process.exit(1);
}

console.log(`Meta Ads OAuth mock safety regression passed (${checks.length} checks).`);
