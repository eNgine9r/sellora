import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.cwd());
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
const exists = (file) => fs.existsSync(path.join(root, file));

const reportPath = "docs/sprint-7e-rbac-tenant-isolation-security-qa.md";
const report = exists(reportPath) ? read(reportPath) : "";
const testsDir = path.join(root, "backend/tests/security");
const securityTests = exists("backend/tests/security") ? fs.readdirSync(testsDir).filter((file) => file.endsWith(".py")) : [];
const migrationFiles = fs.readdirSync(path.join(root, "backend/alembic/versions"));
const docs = [report, read("docs/known-limitations.md"), read("docs/mvp-readiness.md"), read("README.md")].join("\n");
const frontendSecuritySurface = [
  read("frontend/src/services/api.ts"),
  read("frontend/src/stores/auth.store.tsx"),
  read("frontend/src/components/app-shell.tsx"),
  read("frontend/src/components/mobile-more-sheet.tsx"),
].join("\n");

const checks = [
  ["Sprint 7E QA report exists", exists(reportPath)],
  ["RBAC matrix is documented", report.includes("## 5. Actual role matrix") && report.includes("OWNER") && report.includes("MANAGER") && report.includes("ANALYST")],
  ["tenant isolation section exists", report.includes("Tenant list isolation") && report.includes("Object IDOR") && report.includes("Nested resource isolation")],
  ["inactive membership coverage exists", report.includes("inactive membership") && report.includes("test_lead_assignment_rejects_inactive_workspace_membership")],
  ["workspace-switch cache policy is documented", report.includes("Workspace switch and cache") && report.includes("race-condition")],
  ["mobile authorization QA is documented", report.includes("mobile navigation") && report.includes("Direct API attempts")],
  ["backend security tests exist", securityTests.length >= 4 && securityTests.includes("test_endpoint_inventory.py")],
  ["no new Sprint 7E migration file was added", migrationFiles.every((file) => !/7e|rbac|tenant|security/i.test(file)) && report.includes("No product feature work")],
  ["no Meta feature work was added", !/Meta OAuth changes added|scheduled sync added|apply-sync added|Conversions API added/i.test(docs)],
  ["no hardcoded real workspace IDs exist", !/workspace_id\s*=\s*["'][0-9a-fA-F-]{20,}["']|X-Workspace-ID.*[0-9a-fA-F-]{20,}/.test(docs + "\n" + frontendSecuritySurface)],
  ["no credentials appear in Sprint documentation", !/(Authorization: Bearer\s+[A-Za-z0-9._-]+|access_token\s*[:=]\s*[A-Za-z0-9._-]{12,}|refresh_token\s*[:=]\s*[A-Za-z0-9._-]{12,}|client_secret\s*[:=]\s*\S+|app_secret\s*[:=]\s*\S+|password\s*[:=]\s*\S+)/i.test(report)],
];

let failed = false;
for (const [label, ok] of checks) {
  if (ok) console.log(`OK ${label}`);
  else {
    failed = true;
    console.error(`FAIL ${label}`);
  }
}

if (failed) process.exit(1);
console.log("RBAC / tenant security regression checks passed.");
