import { readFileSync } from "node:fs";

const files = {
  importService: readFileSync("backend/app/services/import_center_service.py", "utf8"),
  importSchemas: readFileSync("backend/app/schemas/import_center.py", "utf8"),
  demoSeed: readFileSync("backend/scripts_seed_demo.py", "utf8"),
  importDocs: readFileSync("docs/imports.md", "utf8"),
  demoDocs: readFileSync("docs/demo-dataset.md", "utf8"),
  qaDocs: readFileSync("docs/staging-qa-checklist.md", "utf8"),
  analyticsDocs: readFileSync("docs/analytics-metrics.md", "utf8"),
  importPanel: readFileSync("frontend/src/features/import-center/components/import-report-panel.tsx", "utf8"),
  en: readFileSync("frontend/src/i18n/messages/en.json", "utf8"),
  uk: readFileSync("frontend/src/i18n/messages/uk.json", "utf8"),
  tests: readFileSync("backend/tests/test_import_center.py", "utf8"),
};

const checks = [
  ["product catalog matching hardening", files.importService.includes("_find_product_by_normalized_name") && files.importService.includes("product/color/size")],
  ["historical order customer dedup normalization", files.importService.includes("normalize_phone") && files.importService.includes("normalize_instagram")],
  ["advertising duplicate metric handling", files.importService.includes("Duplicate ad metric skipped")],
  ["dry-run structured result summary", files.importSchemas.includes("errors_by_row") && files.importSchemas.includes("warnings_by_row")],
  ["row-level errors and warnings UI", files.importPanel.includes("errors_by_row") || files.importPanel.includes("sample_errors")],
  ["duplicate and idempotency docs", files.importDocs.includes("Duplicate key") && files.importDocs.includes("Idempotency") || files.demoDocs.includes("Idempotency")],
  ["demo dataset seed", files.demoSeed.includes("DEMO_WORKSPACE_SLUG") && files.demoSeed.includes("DEMO-RING-LUNA")],
  ["analytics verification docs", files.analyticsDocs.includes("Sprint 2.6 Import Analytics Verification") && files.demoDocs.includes("Analytics verification")],
  ["Import Center localization keys", files.en.includes('"imports"') && files.uk.includes('"imports"') && files.en.includes('"dryRun"') && files.uk.includes('"dryRun"')],
  ["no obvious real private data fixture", !/\+380\d{9}|@gmail\.com|@ukr\.net/.test(files.demoSeed + files.importDocs + files.demoDocs)],
  ["backend import tests", files.tests.includes("test_product_catalog_accepts_name_and_color_size_fallback") && files.tests.includes("test_import_report_contains_structured_row_error_warning_counters")],
];

const failed = checks.filter(([, ok]) => !ok);
if (failed.length) {
  console.error(`Import/demo data regression failed: ${failed.map(([name]) => name).join(", ")}`);
  process.exit(1);
}
console.log(`Import/demo data regression passed (${checks.length} checks).`);
