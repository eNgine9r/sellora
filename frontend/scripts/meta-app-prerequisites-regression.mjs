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
    } else if (predicate(fullPath)) files.push(fullPath);
  }
  return files;
};

const requiredFiles = [
  "frontend/src/app/legal/privacy/page.tsx",
  "frontend/src/app/legal/terms/page.tsx",
  "frontend/src/app/legal/data-deletion/page.tsx",
  "docs/legal-url-readiness.md",
  "docs/staging-url-inventory.md",
  "docs/meta-developer-app-input-pack.md",
  "docs/meta-oauth-redirect-uri-plan.md",
  "docs/meta-env-vars-plan.md",
];

for (const file of requiredFiles) expect(`${file} exists`, fs.existsSync(file));

const legalPages = [
  read("frontend/src/app/legal/privacy/page.tsx"),
  read("frontend/src/app/legal/terms/page.tsx"),
  read("frontend/src/app/legal/data-deletion/page.tsx"),
  read("frontend/src/app/legal/_components/legal-page-shell.tsx"),
].join("\n");
const docs = [
  ...requiredFiles.filter((file) => file.startsWith("docs/")),
  "README.md",
  "docs/meta-api-part-6-readiness-plan.md",
  "docs/meta-developer-app-setup-checklist.md",
  "docs/meta-api-staging-qa-checklist.md",
  "docs/meta-live-oauth-design.md",
  "docs/meta-token-storage-design.md",
  "docs/mvp-readiness.md",
  "docs/known-limitations.md",
].map(read).join("\n");
const landing = read("frontend/src/components/landing.tsx");
const login = read("frontend/src/app/login/page.tsx");
const uk = read("frontend/src/i18n/messages/uk.json");
const en = read("frontend/src/i18n/messages/en.json");

expect("legal URL drafts include Privacy Policy", legalPages.includes("Політика конфіденційності") && legalPages.includes("Privacy Policy"));
expect("legal URL drafts include Terms of Service", legalPages.includes("Умови користування") && legalPages.includes("Terms of Service"));
expect("legal URL drafts include Data Deletion", legalPages.includes("Видалення даних") && legalPages.includes("Data Deletion"));
expect("legal review warning visible", legalPages.includes("MVP-чернетками") && legalPages.includes("require qualified legal review") && docs.includes("Legal pages are MVP drafts and require legal review"));
expect("privacy page documents Meta inactive and no customer data sent", legalPages.includes("Meta Ads API ще не активний") && legalPages.includes("не надсилає дані клієнтів до Meta"));
expect("terms page documents finance limitation", legalPages.includes("операційна аналітика прибутку") && legalPages.includes("бухгалтерську"));
expect("data deletion page documents no live Meta data", legalPages.includes("не зберігає live Meta tokens") && legalPages.includes("Future Meta-related deletion handling"));
expect("staging URL inventory documented", docs.includes("frontend_staging_url") && docs.includes("oauth_redirect_uri") && docs.includes("allowed_cors_origins"));
expect("Meta Developer App input pack documented", docs.includes("Meta App name") && docs.includes("App Review notes") && docs.includes("Screencast/demo notes"));
expect("OAuth redirect URI plan documented", docs.includes("Staging callback:") && docs.includes("Callback must be backend-owned for token exchange"));
expect("environment variables plan documented", docs.includes("META_APP_ID") && docs.includes("META_APP_SECRET") && docs.includes("META_TOKEN_ENCRYPTION_KEY"));
expect("server-only secret rules documented", docs.includes("Server-only secret") && docs.includes("`NEXT_PUBLIC` must not be used for secrets"));
expect("public legal links added safely", landing.includes("/legal/privacy") && landing.includes("/legal/terms") && landing.includes("/legal/data-deletion") && login.includes("/legal/privacy"));
expect("i18n legal link keys exist", uk.includes("Політика конфіденційності") && en.includes("Privacy Policy"));
expect("Meta API inactive wording", docs.includes("Meta Ads API is not active."));
expect("Sprint 6A.1 scope wording", docs.includes("Sprint 6A.1 prepares legal URLs, staging URL inventory, Meta App input pack, OAuth redirect URI planning, and environment variable planning only"));
expect("no live OAuth implementation wording", docs.includes("No live OAuth, no token storage, no live API calls, and no production sync were implemented"));
expect("Advertising not pilot-ready", docs.includes("Advertising remains feature-frozen") && docs.includes("not pilot-ready"));
expect("no real credential-looking fixtures", !/EA[A-Za-z0-9]{20,}|act_\d{8,}|Authorization: Bearer\s+[A-Za-z0-9._-]+/.test(`${docs}\n${legalPages}`));

const appCode = [
  ...readFilesRecursive("backend/app", (file) => file.endsWith(".py")),
  ...readFilesRecursive("frontend/src", (file) => /\.(ts|tsx|js|jsx)$/.test(file)),
].map((file) => `${file}\n${read(file)}`).join("\n");
const migrationNames = readFilesRecursive("backend/alembic/versions", (file) => file.endsWith(".py")).map((file) => path.basename(file)).join("\n");

expect("no facebook.com redirect in application code", !/facebook\.com\/(dialog|v\d+\.\d+|oauth)/i.test(appCode));
expect("no graph.facebook.com API call in application code", !/graph\.facebook\.com/i.test(appCode));
expect("Sprint 6B token storage foundation remains gated", /META_TOKEN_STORAGE_ENABLED/i.test(appCode) && /meta_ad_connections/i.test(appCode));
expect("meta_ad_connections migration exists only as guarded Sprint 6B foundation", /meta_ad_connections/i.test(migrationNames));
expect("no Meta API active claim", !/Meta Ads API active|Meta OAuth implemented|Meta account connected|Token storage active/i.test(`${docs}\n${legalPages}`));

const failed = checks.filter((check) => !check.passed);
if (failed.length) {
  console.error("Meta app prerequisites regression failed:");
  for (const check of failed) console.error(`- ${check.name}`);
  process.exit(1);
}

console.log(`Meta app prerequisites regression passed (${checks.length} checks).`);
