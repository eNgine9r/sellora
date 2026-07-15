import { existsSync, readdirSync, readFileSync } from "node:fs";

const read = (path) => readFileSync(path, "utf8");
const files = {
  report: read("docs/sprint-8e-nova-poshta-real-validation.md"),
  contract: read("docs/nova-poshta-provider-contract.md"),
  mapping: read("docs/nova-poshta-status-mapping.md"),
  security: read("docs/nova-poshta-security-and-secrets.md"),
  guide: read("docs/nova-poshta-controlled-pilot-guide.md"),
  release: read("docs/pilot-release-decision.md"),
  service: read("backend/app/services/nova_poshta_service.py"),
  config: read("backend/app/core/config.py"),
  tests: existsSync("backend/tests/integrations/nova_poshta/test_real_validation_guards.py") ? read("backend/tests/integrations/nova_poshta/test_real_validation_guards.py") : "",
  legacyTests: read("backend/tests/test_nova_poshta.py"),
};
const migrations = readdirSync("backend/alembic/versions");
const checks = [
  ["Sprint 8E report exists", files.report.includes("Existing integration inventory") && files.report.includes("TTN creation")],
  ["provider contract exists", files.contract.includes("InternetDocument.save") && files.contract.includes("TrackingDocument.getStatusDocuments")],
  ["status mapping exists", files.mapping.includes("Unknown/unmapped") && files.service.includes("_normalize_provider_status")],
  ["security/secrets document exists", files.security.includes("masked_api_key") && files.security.includes("STAGING_NOVA_POSHTA_ALLOW_WRITES")],
  ["controlled pilot guide exists", files.guide.includes("QA8E") && files.guide.includes("controlled TTN")],
  ["provider writes require server-side flag", files.config.includes("staging_nova_poshta_allow_writes") && files.service.includes("_provider_writes_allowed") && files.tests.includes("test_provider_write_flag_blocks_ttn_before_provider_call")],
  ["key is never returned unmasked", files.legacyTests.includes("masked_api_key") && files.security.includes("never the raw saved API key")],
  ["ANALYST provider mutations denied", files.legacyTests.includes("require_min_role(RoleName.MANAGER)") || files.report.includes("ANALYST provider mutations remain denied")],
  ["workspace isolation documented and tested", files.report.includes("workspace_id") && files.legacyTests.includes("test_cross_workspace_ttn_access")],
  ["duplicate TTN protection exists", files.service.includes("_in_progress_ttn_keys") && files.tests.includes("test_in_progress_guard_blocks_duplicate_ttn")],
  ["retry policy separates read and write", files.report.includes("Non-idempotent provider writes are not automatically retried") && files.guide.includes("Refresh status manually")],
  ["unknown status does not fabricate status", files.mapping.includes("Keep previous normalized") && files.tests.includes("test_unknown_provider_status_keeps_previous_normalized_status")],
  ["no automatic background sync", !/celery|cron|BackgroundTasks|schedule.*nova/i.test(files.service + files.config)],
  ["no new migration", !migrations.some((name) => /8e|nova.*real|ttn.*guard/i.test(name))],
  ["Sprint 8D remains approved", /Sprint 8D.*APPROVED|Orders \/ Inventory \/ Local Shipments.*GREEN/is.test(files.release)],
  ["controlled pilot baseline GREEN", /Controlled guided pilot remains GREEN|Controlled guided pilot.*GREEN/is.test(files.release)],
];
const failed = checks.filter(([, ok]) => !ok);
if (failed.length) {
  console.error(`Nova Poshta real validation regression failed: ${failed.map(([name]) => name).join(", ")}`);
  process.exit(1);
}
console.log(`Nova Poshta real validation regression passed (${checks.length} checks).`);
