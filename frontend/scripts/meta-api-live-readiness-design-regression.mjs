import fs from "node:fs";
import path from "node:path";

const read = (filePath) => fs.readFileSync(filePath, "utf8");
const checks = [];
const expect = (name, condition) => checks.push({ name, passed: Boolean(condition) });

const readFilesRecursive = (dir, predicate = () => true) => {
  const files = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (["node_modules", ".next", "__pycache__"].includes(entry.name)) continue;
      files.push(...readFilesRecursive(fullPath, predicate));
    } else if (predicate(fullPath)) {
      files.push(fullPath);
    }
  }
  return files;
};

const requiredDocs = [
  "docs/meta-developer-app-setup-checklist.md",
  "docs/meta-permissions-plan.md",
  "docs/meta-live-oauth-design.md",
  "docs/meta-token-storage-design.md",
  "docs/meta-connection-status-contract.md",
  "docs/meta-audit-logging-design.md",
  "docs/meta-api-staging-qa-checklist.md",
  "docs/meta-api-part-6-readiness-plan.md",
];

for (const doc of requiredDocs) expect(`${doc} exists`, fs.existsSync(doc));

const docs = Object.fromEntries(requiredDocs.map((doc) => [doc, read(doc)]));
const combinedDocs = Object.values(docs).join("\n");
const coreDocs = [
  read("README.md"),
  read("docs/meta-ads-integration-plan.md"),
  read("docs/meta-ads-technical-design.md"),
  read("docs/mvp-readiness.md"),
  read("docs/known-limitations.md"),
  read("docs/advertising-known-blockers.md"),
  read("docs/finance-readiness.md"),
].join("\n");
const allDocs = `${combinedDocs}\n${coreDocs}`;

expect("Meta Developer App checklist documented", docs["docs/meta-developer-app-setup-checklist.md"].includes("Meta Developer App required") && docs["docs/meta-developer-app-setup-checklist.md"].includes("Before implementing live OAuth"));
expect("permissions plan documented", docs["docs/meta-permissions-plan.md"].includes("Phase 1 — read-only insights") && docs["docs/meta-permissions-plan.md"].includes("ads_read") && docs["docs/meta-permissions-plan.md"].includes("Do not over-request"));
expect("live OAuth design documented", docs["docs/meta-live-oauth-design.md"].includes("Backend creates signed OAuth state") && docs["docs/meta-live-oauth-design.md"].includes("OWNER-only connect"));
expect("secure token storage design documented", docs["docs/meta-token-storage-design.md"].includes("Encrypted access token storage") && docs["docs/meta-token-storage-design.md"].includes("Do not add this migration in Sprint 6A"));
expect("connection status contract documented", docs["docs/meta-connection-status-contract.md"].includes("NOT_CONNECTED") && docs["docs/meta-connection-status-contract.md"].includes("MOCK_ONLY") && docs["docs/meta-connection-status-contract.md"].includes("backend enum values"));
expect("audit logging design documented", docs["docs/meta-audit-logging-design.md"].includes("meta_ads_connect_started") && docs["docs/meta-audit-logging-design.md"].includes("No raw token"));
expect("staging QA checklist documented", docs["docs/meta-api-staging-qa-checklist.md"].includes("OWNER test user") && docs["docs/meta-api-staging-qa-checklist.md"].includes("Pilot-ready rule"));
expect("Part 6 sequence remains documented", docs["docs/meta-api-part-6-readiness-plan.md"].includes("Part 6.0") && docs["docs/meta-api-part-6-readiness-plan.md"].includes("Part 6.4"));
expect("Meta API not active wording present", allDocs.includes("Meta Ads API is not active."));
expect("Sprint 6A is design only", allDocs.includes("Sprint 6A prepares setup, security, OAuth, token storage, and QA design only"));
expect("no live OAuth implementation claim", allDocs.includes("No live OAuth, no token storage, no live API calls, and no production sync were implemented"));
expect("Advertising not pilot-ready guardrail", allDocs.includes("Advertising remains feature-frozen and not pilot-ready"));
expect("Conversions API future-only", allDocs.includes("Conversions API remains") && allDocs.includes("future"));
expect("Finance blockers remain tracked", allDocs.includes("Finance 5.x remains locally validated with runtime migration QA and browser/mobile QA blockers tracked separately"));

const appFiles = [
  ...readFilesRecursive("backend/app", (file) => file.endsWith(".py")),
  ...readFilesRecursive("frontend/src", (file) => /\.(ts|tsx|js|jsx)$/.test(file)),
];
const appCode = appFiles.map((file) => `${file}\n${read(file)}`).join("\n");
const migrationFiles = readFilesRecursive("backend/alembic/versions", (file) => file.endsWith(".py"));
const migrationNames = migrationFiles.map((file) => path.basename(file)).join("\n");

expect("no facebook.com redirect in application code", !/facebook\.com\/(dialog|v\d+\.\d+|oauth)/i.test(appCode));
expect("no graph.facebook.com API call in application code", !/graph\.facebook\.com/i.test(appCode));
expect("no live token storage implementation in application code", !/meta_ad_connections/i.test(appCode));
expect("no meta_ad_connections migration", !/meta_ad_connections/i.test(migrationNames));
expect("no active sync wording in app code", !/live Meta sync active|Meta Ads connected|Meta Ads API active/i.test(appCode));
expect("no pilot-ready advertising claim", !/Advertising is pilot-ready|Advertising import is pilot-ready|Meta Ads API is pilot-ready/i.test(allDocs));
expect("no real Meta token/account fixtures", !/EA[A-Za-z0-9]{20,}|act_\d{8,}|Authorization: Bearer\s+[A-Za-z0-9._-]+/.test(allDocs));

const failed = checks.filter((check) => !check.passed);
if (failed.length) {
  console.error("Meta API live readiness design regression failed:");
  for (const check of failed) console.error(`- ${check.name}`);
  process.exit(1);
}

console.log(`Meta API live readiness design regression passed (${checks.length} checks).`);
