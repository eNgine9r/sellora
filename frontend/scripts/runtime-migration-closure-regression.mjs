import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const read = (rel) => fs.readFileSync(path.join(root, rel), "utf8");
const exists = (rel) => fs.existsSync(path.join(root, rel));
const reportPath = "docs/sprint-7f-runtime-migration-closure.md";
const report = exists(reportPath) ? read(reportPath) : "";
const combined = [
  report,
  read("docs/mvp-readiness.md"),
  read("docs/known-limitations.md"),
  read("docs/admin-roles-users.md"),
  read("docs/workspace-management.md"),
].join("\n");

const forbiddenSecretPatterns = [
  /postgresql\+psycopg:\/\//i,
  /(?:test){2}/i,
  /Authorization:\s*Bearer/i,
  /access_token\s*[:=]\s*[A-Za-z0-9._-]+/i,
  /refresh_token\s*[:=]\s*[A-Za-z0-9._-]+/i,
];

const checks = [
  ["Sprint 7F migration closure report exists", exists(reportPath)],
  ["report contains migration inventory section", report.includes("## 5. Alembic inventory")],
  ["report contains pre-upgrade revision section", report.includes("## 7. Pre-upgrade revision")],
  ["report contains upgrade result section", report.includes("## 8. Upgrade result")],
  ["report contains post-upgrade revision section", report.includes("## 9. Post-upgrade revision")],
  ["report contains runtime schema verification section", report.includes("## 10. Runtime schema verification")],
  ["report contains rollback policy section", report.includes("## 14. Downgrade/rollback policy")],
  ["report does not contain connection strings or credentials", !forbiddenSecretPatterns.some((pattern) => pattern.test(report))],
  ["report records no migration file changes", report.includes("No migration files")],
  ["no Meta feature work was added", !/Meta Ads API feature work added|Meta OAuth changes added|scheduled sync added|apply-sync added/i.test(combined)],
];

let failed = false;
for (const [label, ok] of checks) {
  if (ok) console.log(`OK ${label}`);
  else {
    console.error(`FAIL ${label}`);
    failed = true;
  }
}
if (failed) process.exit(1);
