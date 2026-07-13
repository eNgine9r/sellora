import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.cwd());
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
const exists = (file) => fs.existsSync(path.join(root, file));
const failures = [];
const assert = (condition, message) => { if (!condition) failures.push(message); };

const report = read("docs/sprint-7e1-security-closure-frontend-ci.md");
const auditBacklog = read("docs/security-audit-logging-backlog.md");
const injectionTest = read("backend/tests/security/test_workspace_injection.py");
const endpointInventory = read("backend/tests/security/test_endpoint_inventory.py");
const authStore = read("frontend/src/stores/auth.store.tsx");
const workspacePages = [
  "frontend/src/app/dashboard/page.tsx",
  "frontend/src/app/leads/page.tsx",
  "frontend/src/app/orders/page.tsx",
  "frontend/src/app/customers/page.tsx",
  "frontend/src/app/inventory/page.tsx",
  "frontend/src/app/shipments/page.tsx",
  "frontend/src/app/advertising/page.tsx",
  "frontend/src/app/finance/page.tsx",
  "frontend/src/app/analytics/page.tsx",
].map(read).join("\n");
const docs = [report, auditBacklog, read("docs/sprint-7e-rbac-tenant-isolation-security-qa.md"), read("docs/mvp-readiness.md"), read("docs/known-limitations.md"), read("README.md")].join("\n");
const migrationFiles = fs.readdirSync(path.join(root, "backend/alembic/versions"));

assert(exists("docs/sprint-7e1-security-closure-frontend-ci.md"), "Sprint 7E.1 report must exist.");
assert(exists("backend/tests/security/test_workspace_injection.py"), "Explicit workspace-injection test file must exist.");
assert(/test_create_payload_workspace_injection/.test(injectionTest) && injectionTest.includes("workspace_id"), "Create workspace injection scenario must exist.");
assert(/test_update_payload_workspace_injection/.test(injectionTest) && injectionTest.includes("tenant_id"), "Update workspace injection scenario must exist.");
assert(/test_nested_cross_workspace_reference_injection/.test(injectionTest) && injectionTest.includes("owner_workspace_id"), "Nested tenant reference scenario must exist.");
assert(exists("frontend/package-lock.json"), "frontend/package-lock.json must exist.");
assert(report.includes("npm --prefix frontend ci") && report.includes("No package manager switch"), "Lockfile recovery and npm CI policy must be documented.");
assert(endpointInventory.includes("EXPECTED_PRIMARY_COUNTS") && endpointInventory.includes("EXPECTED_TOTAL_ROUTES = 153") && report.includes("Primary classification total"), "Route inventory totals must be exact and documented.");
assert(auditBacklog.includes("Role change") && auditBacklog.includes("Finance adjustments") && auditBacklog.includes("must never store passwords"), "Audit logging backlog must cover required events and secret-safety rule.");
assert(authStore.includes("queryClient.cancelQueries") && authStore.includes("queryClient.invalidateQueries") && authStore.includes("queryClient.clear"), "Workspace switch/logout cache handling must cancel, invalidate and clear private cache.");
for (const key of ["dashboard", "leads", "orders", "customers", "inventory", "shipments"]) {
  assert(new RegExp(`\\[\"[^\"]*${key}[^\"]*\",\\s*workspaceId`).test(workspacePages) || new RegExp(`\\[\"[^\"]*${key}[^\"]*\",\\s*currentWorkspaceId`).test(workspacePages), `${key} query keys must include workspace ID.`);
}
assert(/setSelected(Order|Lead|Customer|Inventory|Shipment)\(null\)/.test(workspacePages), "Workspace-bound selected detail state must be cleared on workspace change.");
assert(report.includes("Sprint 7F Runtime Migration Closure — BLOCKED"), "Sprint 7F must remain separately blocked.");
assert(migrationFiles.every((file) => !/7e1|security_closure|workspace_injection|audit/i.test(file)), "No Sprint 7E.1 migration should be added.");
assert(!/Meta OAuth changes added|live Meta sync enabled|Conversions API added/i.test(docs), "No Meta feature scope should be added.");
assert(!/workspace_id\s*=\s*["'][0-9a-fA-F-]{20,}["']|X-Workspace-ID.*[0-9a-fA-F-]{20,}/.test(docs + "\n" + authStore), "No hardcoded real workspace IDs should be committed.");
assert(!/(Authorization: Bearer\s+[A-Za-z0-9._-]+|access_token\s*[:=]\s*[A-Za-z0-9._-]{12,}|refresh_token\s*[:=]\s*[A-Za-z0-9._-]{12,}|client_secret\s*[:=]\s*\S+|app_secret\s*[:=]\s*\S+)/i.test(docs), "No credentials should appear in closure docs.");

if (failures.length) {
  console.error("Security closure CI regression failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}
console.log("Security closure CI regression checks passed.");
