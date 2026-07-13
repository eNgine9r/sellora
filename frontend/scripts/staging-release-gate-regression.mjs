import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
const exists = (file) => fs.existsSync(path.join(root, file));
const failures = [];
const assert = (condition, message) => { if (!condition) failures.push(message); };

const report = read("docs/sprint-8a-staging-release-gate.md");
const checklist = read("docs/staging-release-checklist.md");
const issues = read("docs/staging-release-issues.md");
const decision = read("docs/pilot-release-decision.md");
const closure = read("docs/sprint-8a1-staging-e2e-closure.md");
const readiness = read("docs/mvp-readiness.md");
const limitations = read("docs/known-limitations.md");
const readme = read("README.md");
const runner = read("scripts/staging_release_gate.py");
const combinedDocs = [report, closure, checklist, issues, decision, readiness, limitations, readme].join("\n");
const migrationFiles = fs.readdirSync(path.join(root, "backend/alembic/versions"));

assert(exists("docs/sprint-8a-staging-release-gate.md"), "Sprint 8A report must exist.");
assert(exists("docs/staging-release-checklist.md"), "Staging release checklist must exist.");
assert(exists("docs/staging-release-issues.md"), "Staging release issue log must exist.");
assert(exists("docs/pilot-release-decision.md"), "Pilot release decision must exist.");
assert(exists("scripts/staging_release_gate.py"), "Staging release gate runner must exist.");
assert(exists("docs/sprint-8a1-staging-e2e-closure.md"), "Sprint 8A.1 closure report must exist.");
assert(report.includes("## 3. Release manifest") && report.includes("Frontend") && report.includes("Backend") && report.includes("Database"), "Release manifest section must exist.");
assert(report.includes("## 17. OWNER result") && report.includes("## 18. MANAGER result") && report.includes("## 19. ANALYST result"), "OWNER/MANAGER/ANALYST coverage must be documented.");
assert(report.includes("## 11. Gate G6 result — Orders") && checklist.includes("Synthetic order can be created"), "Core order flow coverage must be documented.");
assert(report.includes("## 15. Gate G10 result — Mobile/PWA") && checklist.includes("375×812"), "Mobile coverage must be documented.");
assert(combinedDocs.includes("Sprint 7F") && combinedDocs.includes("BLOCKED"), "Sprint 7F must remain explicitly blocked.");
assert(migrationFiles.every((file) => !/8a|staging_release|pilot_release/i.test(file)), "Sprint 8A must not add an Alembic migration.");
assert(!/live Meta sync enabled|Meta OAuth changes added|Conversions API added/i.test(combinedDocs), "Sprint 8A must not add Meta feature scope.");
assert(!/(Authorization: Bearer\s+[A-Za-z0-9._-]+|access_token\s*[:=]\s*[A-Za-z0-9._-]{12,}|refresh_token\s*[:=]\s*[A-Za-z0-9._-]{12,}|client_secret\s*[:=]\s*\S+|app_secret\s*[:=]\s*\S+)/i.test(combinedDocs), "No real credentials or tokens should be committed.");
assert(!/(\+380\d{9}|[A-Z0-9._%+-]+@(gmail\.com|ukr\.net))/i.test(combinedDocs), "No real-looking phone numbers or personal emails should be committed.");
assert(!/real customer data was used|real order data was used|production customer/i.test(combinedDocs), "No real customer/order data should be committed.");
assert(/GREEN|YELLOW|RED/.test(decision), "Final GREEN/YELLOW/RED decision must be recorded.");
assert(/Sprint 8A\.1/.test(closure) && closure.includes("Controlled-write E2E result"), "8A.1 status and controlled-write result must be documented.");
assert(runner.includes("STAGING_ALLOW_CONTROLLED_WRITES") && runner.includes("token suppressed") && runner.includes("ARTIFACT_PATH"), "Runner must guard writes, suppress tokens and emit an artifact.");
assert(runner.includes("STAGING_OWNER_EMAIL") && runner.includes("STAGING_MANAGER_EMAIL") && runner.includes("STAGING_ANALYST_EMAIL"), "Runner must support all role credential inputs.");

if (failures.length) {
  console.error("Staging release gate regression failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log("Staging release gate regression checks passed.");
