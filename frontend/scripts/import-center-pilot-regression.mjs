import { existsSync, readdirSync, readFileSync } from "node:fs";

const read = (path) => readFileSync(path, "utf8");
const files = {
  report: read("docs/sprint-8c-import-center-pilot-hardening.md"),
  contracts: read("docs/import-template-contracts.md"),
  catalog: read("docs/import-validation-error-catalog.md"),
  guide: read("docs/pilot-import-guide.md"),
  security: read("docs/import-security-and-data-handling.md"),
  service: read("backend/app/services/import_center_service.py"),
  durable: read("backend/app/services/import_durable_service.py"),
  storage: read("backend/app/services/import_source_storage.py"),
  guard: read("backend/app/services/import_execution_guard.py"),
  audit: read("backend/app/repositories/audit_log_repository.py"),
  importRepository: read("backend/app/repositories/import_center_repository.py"),
  api: read("backend/app/api/v1/import_center.py"),
  tests: existsSync("backend/tests/imports/test_import_center_pilot_hardening.py") ? read("backend/tests/imports/test_import_center_pilot_hardening.py") : "",
  guardTests: existsSync("backend/tests/imports/test_import_execution_guard.py") ? read("backend/tests/imports/test_import_execution_guard.py") : "",
  scopeTests: existsSync("backend/tests/imports/test_import_pilot_scope_safety.py") ? read("backend/tests/imports/test_import_pilot_scope_safety.py") : "",
  page: read("frontend/src/app/settings/import/page.tsx"),
  upload: read("frontend/src/features/import-center/components/import-upload-card.tsx"),
  validationIssues: read("frontend/src/features/import-center/components/validation-issues-table.tsx"),
  reportPanel: read("frontend/src/features/import-center/components/import-report-panel.tsx"),
  pilotCopy: read("frontend/src/features/import-center/import-center-pilot-copy.ts"),
  uk: read("frontend/src/i18n/messages/uk.json"),
  en: read("frontend/src/i18n/messages/en.json"),
  release: read("docs/pilot-release-decision.md"),
  eightB: read("docs/sprint-8b-demo-data-first-run.md"),
};
const combined = Object.entries(files).filter(([name]) => name !== "guardTests").map(([, value]) => value).join("\n");
const migrationNames = readdirSync("backend/alembic/versions");
const checks = [
  ["Sprint 8C report exists", existsSync("docs/sprint-8c-import-center-pilot-hardening.md") && files.report.includes("Existing capability inventory")],
  ["template contracts exist", files.contracts.includes("Supported pilot formats and limits") && files.contracts.includes("Duplicate policy")],
  ["validation error catalog exists", files.catalog.includes("FORMULA_INJECTION_RISK") && files.catalog.includes("DUPLICATE_HEADERS")],
  ["pilot guide exists", files.guide.includes("Run validation and dry-run") && files.guide.includes("Do not use Meta Ads live sync")],
  ["dry-run required before execute", files.service.includes("Successful dry-run is required before import execution") && files.page.includes("approvedDryRunKey !== dryRunKey")],
  ["persisted dry-run signature guard", files.guard.includes("IMPORT_DRY_RUN_APPROVED_ACTION") && files.guard.includes("file_sha256") && files.guard.includes("require_matching_dry_run") && files.audit.includes("latest_action_value") && files.api.includes("guard.require_matching_dry_run") && files.guardTests.includes("test_persisted_signature_survives_new_guard_instance")],
  ["durable source storage exists", files.durable.includes("DurableImportService") && files.storage.includes('URI_SCHEME = "supabase"') && files.storage.includes('return f"{self.URI_SCHEME}://') && files.storage.includes("assert_workspace_job_location")],
  ["duplicate policy documented", /Default pilot behavior is safe skip\/warning\/reject|Default pilot policy is `SKIP`/i.test(files.report + files.contracts)],
  ["workspace-switch clears import state", files.page.includes("useEffect") && files.page.includes("setDryRunReport(undefined)") && files.security.includes("Workspace switch behavior")],
  ["ANALYST execute denial exists", files.tests.includes("test_analyst_execute_denied") && files.security.includes("ANALYST")],
  ["rollback test exists", files.report.includes("Rollback behavior") && files.tests.includes("dry_run_sets_validated_status")],
  ["historical order side effects documented", files.report.includes("Historical order semantics") && files.report.includes("does not call external shipment providers")],
  ["shipments import disabled for controlled pilot", files.durable.includes('PILOT_UNSUPPORTED_ENTITY_TYPES = {"shipments"}') && files.scopeTests.includes("test_shipments_import_is_explicitly_unsupported")],
  ["historical order shipment fields ignored", files.durable.includes("HISTORICAL_ORDER_IGNORED_FIELDS") && files.scopeTests.includes("test_historical_order_mapping_ignores_shipment_side_effect_fields")],
  ["unknown historical statuses rejected", files.durable.includes("historical_status_issues") && files.scopeTests.includes("test_unknown_historical_order_and_payment_statuses_are_errors")],
  ["raw source rows are not persisted", files.importRepository.includes("log.raw_data = None") && files.scopeTests.includes("test_import_log_repository_never_persists_raw_source_row")],
  ["localized validation UI exists", files.validationIssues.includes("localizeImportIssue") && files.pilotCopy.includes("Некоректне значення")],
  ["safe error CSV download exists", files.reportPanel.includes("data-import-error-csv-download") && files.reportPanel.includes("escapeImportCsvCell")],
  ["truthful historical order help exists", files.page.includes("pilotCopy.ordersHistoryHelp") && files.pilotCopy.includes("не створює відправлення автоматично")],
  ["CSV formula injection protection exists", files.service.includes("escape_csv_formula") && files.reportPanel.includes("escapeImportCsvCell") && (files.catalog.includes("Values beginning with") || files.security.includes("prevent spreadsheet formula injection"))],
  ["no new migration was added", !migrationNames.some((name) => /8c|import.*pilot|dry.*run/i.test(name))],
  ["no real customer file was committed", !/@gmail\.com|@ukr\.net|\+380\d{9}/i.test(combined)],
  ["no Meta/Nova external calls added", !/graph\.facebook|Meta Ads API request|api\.novaposhta\.ua.*import/i.test(files.service + files.durable + files.page + files.contracts)],
  ["Sprint 8B remains approved", /Sprint 8B.*APPROVED|Sprint 8B — APPROVED|Controlled guided pilot.*GREEN/is.test(files.eightB + files.release)],
  ["controlled pilot remains GREEN", /Controlled guided pilot remains GREEN|Controlled guided pilot.*GREEN/is.test(files.release)],
  ["Ukrainian and English import strings exist", files.uk.includes('"uploadLimits"') && files.en.includes('"uploadLimits"')],
];
const failed = checks.filter(([, ok]) => !ok);
if (failed.length) {
  console.error(`Import Center pilot regression failed: ${failed.map(([name]) => name).join(", ")}`);
  process.exit(1);
}
console.log(`Import Center pilot regression passed (${checks.length} checks).`);
