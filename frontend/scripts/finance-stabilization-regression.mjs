import { readFileSync } from "node:fs";

const files = {
  readiness: readFileSync("docs/finance-readiness.md", "utf8"),
  part6: readFileSync("docs/meta-api-part-6-readiness-plan.md", "utf8"),
  limitations: readFileSync("docs/known-limitations.md", "utf8"),
  mvp: readFileSync("docs/mvp-readiness.md", "utf8"),
  financePage: readFileSync("frontend/src/app/finance/page.tsx", "utf8"),
  financeService: readFileSync("backend/app/services/finance_service.py", "utf8"),
  financeApi: readFileSync("backend/app/api/v1/finance.py", "utf8"),
  authScript: readFileSync("frontend/scripts/auth-api-boundary-regression.mjs", "utf8"),
};
const docs = files.readiness + files.part6 + files.limitations + files.mvp;
const code = files.financePage + files.financeService + files.financeApi;
const checks = [
  ["Finance readiness matrix exists", files.readiness.includes("Finance 5.x — implementation-ready / locally validated / runtime migration QA pending") && files.readiness.includes("| Finance adjustments |")],
  ["migration runtime QA pending wording", docs.includes("Finance adjustments migration has passed static Alembic chain validation, but PostgreSQL runtime migration QA remains pending")],
  ["manual adjustments still supported", code.includes("manual_expenses") && code.includes("/adjustments") && code.includes("data-finance-adjustments-ui")],
  ["breakdown and trends present", files.financeApi.includes('"/breakdown"') && files.financeApi.includes('"/trends"') && files.financePage.includes("data-finance-breakdown")],
  ["operational analytics not accounting/tax reporting", docs.includes("operational profit analytics, not full accounting or tax reporting")],
  ["manual/CSV Advertising warning", docs.includes("Advertising data remains a conditional manual/CSV source") && files.financePage.includes("data-finance-manual-csv-warning")],
  ["Meta Ads API inactive", docs.includes("Meta Ads API is not active")],
  ["browser/mobile QA pending documented", docs.includes("Browser/mobile QA") && docs.includes("pending")],
  ["no pilot-ready false claim", docs.includes("not pilot-ready until") && !docs.includes("Finance 5.x is pilot-ready")],
  ["no live Meta implementation", !/graph\.facebook\.com|facebook\.com\/v|access_token\s*=|client_secret\s*=/i.test(files.part6 + code)],
  ["auth boundary regression retained", files.authScript.includes("NEXT_PUBLIC_API_BASE_URL") && files.authScript.includes("/auth/login")],
  ["date range validation is present", files.financeService.includes("date_from must be before or equal to date_to") && files.financeApi.includes("except FinanceServiceError")],
];
let failed = false;
for (const [label, ok] of checks) {
  if (!ok) {
    console.error(`Finance stabilization regression failed: ${label}`);
    failed = true;
  }
}
if (failed) process.exit(1);
console.log(`Finance stabilization regression passed (${checks.length} checks).`);
