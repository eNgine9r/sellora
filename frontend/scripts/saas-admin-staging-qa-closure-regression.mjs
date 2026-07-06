import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const read = (rel) => fs.readFileSync(path.join(root, rel), "utf8");
const exists = (rel) => fs.existsSync(path.join(root, rel));
const reportPath = "docs/sprint-7a1-saas-admin-staging-qa-closure.md";
const report = exists(reportPath) ? read(reportPath) : "";
const combined = [
  report,
  read("docs/admin-roles-users.md"),
  read("docs/workspace-management.md"),
  read("docs/mvp-readiness.md"),
  read("frontend/src/components/app-topbar.tsx"),
  read("frontend/src/components/profile-menu.tsx"),
  read("frontend/src/components/mobile-more-sheet.tsx"),
].join("\n");

const checks = [
  ["Sprint 7A.1 QA report exists", exists(reportPath)],
  ["staging URLs documented without credentials", report.includes("https://sellora-web-staging.vercel.app") && report.includes("https://sellora-api-staging.onrender.com") && !/(?:test){2}/i.test(report)],
  ["role QA sections exist", report.includes("OWNER login QA") && report.includes("MANAGER login QA") && report.includes("ANALYST login QA")],
  ["workspace creation QA section exists", report.includes("Workspace creation QA")],
  ["workspace switching QA section exists", report.includes("Workspace switching QA")],
  ["team management QA section exists", report.includes("Team management QA")],
  ["topbar/mobile QA sections exist", report.includes("Topbar/profile desktop QA") && report.includes("Mobile More sheet QA")],
  ["data isolation QA section exists", report.includes("Data isolation QA")],
  ["runtime migration QA section exists", report.includes("Runtime migration QA") && report.includes("202607050019_admin_roles_users")],
  ["no passwords are committed in QA closure report", !/(?:test){2}|password:\s*\S+|пароль:\s*\S+/i.test(report)],
  ["no Meta-specific work was added", report.includes("No Meta-specific logic") && !/Meta Ads API work was added|Meta OAuth was added|apply-sync was added/i.test(combined)],
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
