import { readFileSync } from "node:fs";

const checks = [
  ["backend model", "backend/app/models/finance_adjustment.py", ["FinanceAdjustmentType", "EXPENSE", "REFUND", "DISCOUNT", "FEE", "WorkspaceScopedMixin"]],
  ["migration", "backend/alembic/versions/202607020017_finance_adjustments.py", ["finance_adjustments", "amount > 0", "downgrade"]],
  ["backend schemas", "backend/app/schemas/finance.py", ["FinanceAdjustmentCreate", "manual_expenses", "FinancePeriodComparisonResponse"]],
  ["backend service", "backend/app/services/finance_service.py", ["manual_expenses", "manual_refunds", "manual_discounts", "manual_fees", "Net profit", "manual_adjustments_may_be_incomplete"]],
  ["frontend finance UI", "frontend/src/app/finance/page.tsx", ["data-finance-adjustments-ui", "data-finance-breakdown", "period-comparison", "expense-refund-discount-fee", "meta-ads-api-not-active"]],
  ["frontend service", "frontend/src/services/finance.ts", ["/finance/adjustments", "/finance/trends", "createFinanceAdjustment"]],
  ["uk i18n", "frontend/src/i18n/messages/uk.json", ["Витрати та коригування", "Ручні повернення", "Ручні знижки", "не повна бухгалтерія"]],
  ["en i18n", "frontend/src/i18n/messages/en.json", ["Expenses and adjustments", "Manual refunds", "Manual discounts", "not full accounting"]],
  ["docs", "docs/finance-adjustments.md", ["operational profit analytics", "not full accounting or tax reporting", "Advertising data remains a conditional manual/CSV source", "Meta Ads API is not active"]],
];
const forbidden = ["live Meta API", "Meta OAuth", "token storage", "pilot-ready Advertising"];
let failed = false;
for (const [label, file, markers] of checks) {
  const source = readFileSync(file, "utf8");
  for (const marker of markers) {
    if (!source.includes(marker)) {
      console.error(`Missing ${label} marker: ${marker}`);
      failed = true;
    }
  }
}
const financePage = readFileSync("frontend/src/app/finance/page.tsx", "utf8");
for (const marker of forbidden) {
  if (financePage.includes(marker)) {
    console.error(`Forbidden live/future marker in finance page: ${marker}`);
    failed = true;
  }
}
if (failed) process.exit(1);
console.log("Finance advanced analytics regression passed.");
