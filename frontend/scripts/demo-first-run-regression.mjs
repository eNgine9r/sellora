import { existsSync, readdirSync, readFileSync } from "node:fs";

const read = (path) => readFileSync(path, "utf8");
const files = {
  report: read("docs/sprint-8b-demo-data-first-run.md"),
  dataset: read("docs/demo-workspace-dataset.md"),
  guide: read("docs/pilot-first-run-guide.md"),
  onboardingApi: read("backend/app/api/v1/onboarding.py"),
  onboardingService: read("backend/app/services/onboarding_service.py"),
  workspaceService: read("backend/app/services/workspace_service.py"),
  auditRepository: read("backend/app/repositories/audit_log_repository.py"),
  dashboard: read("frontend/src/app/dashboard/page.tsx"),
  pilot: read("frontend/src/components/pilot-readiness.tsx"),
  uk: read("frontend/src/i18n/messages/uk.json"),
  en: read("frontend/src/i18n/messages/en.json"),
  release: read("docs/pilot-release-decision.md"),
};
const combined = Object.values(files).join("\n");
const migrationNames = readdirSync("backend/alembic/versions");
const checks = [
  ["Sprint 8B report exists", existsSync("docs/sprint-8b-demo-data-first-run.md") && files.report.includes("Pre-implementation inventory")],
  ["demo dataset document exists", files.dataset.includes("Demo workspace dataset") && files.dataset.includes("never inserted into a user's real workspace")],
  ["first-run guide exists", files.guide.includes("Почати зі своїми даними") && files.guide.includes("Переглянути демо Sellora")],
  ["separate demo workspace decision documented", files.report.includes("separate `Демо Sellora` workspace")],
  ["no demo insertion into real workspace by default", /never inserted into (a user's )?real workspace/i.test(files.dataset + files.report)],
  ["onboarding status workspace scoped", files.onboardingApi.includes("get_workspace_id") && files.onboardingService.includes("get_active_membership")],
  ["role behavior documented", files.report.includes("OWNER can") && files.report.includes("MANAGER") && files.report.includes("ANALYST")],
  ["idempotency uses server provenance", files.workspaceService.includes("has_demo_workspace_provenance") && files.auditRepository.includes("DEMO_WORKSPACE_CREATE_ACTION") && files.report.includes("Idempotency")],
  ["demo eligibility ignores name and slug", files.auditRepository.includes("Workspace names, slugs, and record contents are intentionally ignored") && !files.onboardingService.includes("is_demo_workspace_slug")],
  ["rollback covered", files.workspaceService.includes("self.db.rollback()") && files.report.includes("Rollback behavior")],
  ["query cache cleared for demo lifecycle", files.pilot.includes("queryClient.clear()")],
  ["no external Meta/Nova write path", !/novaposhta|nova.?poshta|graph\.facebook|meta.*post/i.test(files.workspaceService)],
  ["no new migration was added", !migrationNames.some((name) => /8b|onboarding|demo/i.test(name))],
  ["core demo scope is truthful", files.dataset.includes("Core demo scope") && files.dataset.includes("No shipment drafts") && files.dataset.includes("No advertising campaigns or metrics")],
  ["no real customer data committed", !/\+380\d{9}|@gmail\.com|@ukr\.net|реальний пароль/i.test(combined)],
  ["Ukrainian and English strings exist", files.uk.includes('"gettingStarted"') && files.en.includes('"gettingStarted"') && files.uk.includes('"viewDemo"') && files.en.includes('"viewDemo"')],
  ["Sprint 8A.1 remains GREEN", /GREEN|APPROVED|GO FOR CONTROLLED GUIDED PILOT/i.test(files.release)],
];
const failed = checks.filter(([, ok]) => !ok);
if (failed.length) {
  console.error(`Demo first-run regression failed: ${failed.map(([name]) => name).join(", ")}`);
  process.exit(1);
}
console.log(`Demo first-run regression passed (${checks.length} checks).`);
