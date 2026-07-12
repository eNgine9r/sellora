import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
const exists = (file) => fs.existsSync(path.join(root, file));
const failures = [];
const assert = (condition, message) => { if (!condition) failures.push(message); };

const report = read("docs/sprint-8a1-staging-e2e-closure.md");
const gate = read("docs/sprint-8a-staging-release-gate.md");
const issues = read("docs/staging-release-issues.md");
const decision = read("docs/pilot-release-decision.md");
const readiness = read("docs/mvp-readiness.md");
const limitations = read("docs/known-limitations.md");
const readme = read("README.md");
const runner = read("scripts/staging_release_gate.py");
const docs = [report, gate, issues, decision, readiness, limitations, readme].join("\n");
const migrationFiles = fs.readdirSync(path.join(root, "backend/alembic/versions"));

assert(exists("docs/sprint-8a1-staging-e2e-closure.md"), "Sprint 8A.1 report must exist.");
for (const marker of [
  "## 6. Runtime Alembic result",
  "## 7. Read-only smoke result",
  "## 12. Controlled-write E2E result",
  "## 8. OWNER result",
  "## 9. MANAGER result",
  "## 10. ANALYST result",
  "## 11. Workspace switching result",
  "## 14. Browser/mobile result",
  "## 16. Cleanup result",
  "## 21. Release decision",
]) {
  assert(report.includes(marker), `${marker} must be documented.`);
}
assert(report.includes("Sprint 8A.1 — BLOCKED") && gate.includes("Sprint 8A — BLOCKED") && decision.includes("RED — NO-GO"), "Blocked sprint and RED release decision must remain explicit.");
assert(docs.includes("Sprint 7F") && docs.includes("blocked"), "Sprint 7F status must remain explicit.");
assert(issues.includes("8A1-QA-001") && issues.includes("8A1-QA-002") && issues.includes("8A1-QA-003"), "8A.1 issue IDs must be registered.");
assert(runner.includes('run_id = f"8A1-') && runner.includes('"expected_revision"') && runner.includes('"core_e2e"') && runner.includes('"workspace_switching"'), "Runner artifact must include 8A.1 run ID and required closure fields.");
assert(migrationFiles.every((file) => !/8a1|staging_e2e|runtime_compatibility/i.test(file)), "Sprint 8A.1 must not add an Alembic migration.");
assert(!/live Meta sync enabled|Meta OAuth changes added|Conversions API added|real Nova Poshta TTN created/i.test(docs), "No Meta/Nova Poshta external write scope should be added.");
assert(!/(Authorization: Bearer\s+[A-Za-z0-9._-]+|access_token\s*[:=]\s*[A-Za-z0-9._-]{12,}|refresh_token\s*[:=]\s*[A-Za-z0-9._-]{12,}|client_secret\s*[:=]\s*\S+|app_secret\s*[:=]\s*\S+)/i.test(docs), "No credentials or tokens should be committed.");
assert(!/workspace_id\s*=\s*["'][0-9a-fA-F-]{20,}["']|X-Workspace-ID.*[0-9a-fA-F-]{20,}/.test(docs + "\n" + runner), "No real workspace ID should be committed.");
assert(!/(\+380\d{9}|[A-Z0-9._%+-]+@(gmail\.com|ukr\.net)|real customer data was used|real order data was used)/i.test(docs), "No real customer/order data should be committed.");

if (failures.length) {
  console.error("Staging E2E closure regression failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log("Staging E2E closure regression checks passed.");
