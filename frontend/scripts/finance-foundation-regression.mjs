import { readFileSync } from "node:fs";

const checks = [
  ["frontend/src/app/finance/page.tsx", ["data-finance-kpi-card", "data-finance-loading-state", "data-finance-empty-state", "data-finance-error-state", "data-finance-manual-csv-warning", "meta-ads-api-not-active"]],
  ["frontend/src/services/finance.ts", ["/finance/summary", "date_from", "date_to"]],
  ["frontend/src/types/finance.ts", ["FinanceSummary", "data_quality_warnings", "profit_margin", "average_order_value"]],
  ["frontend/src/i18n/messages/uk.json", ["Чистий прибуток", "Рекламні витрати", "Meta Ads API ще не активний", "операційна аналітика прибутку"]],
  ["frontend/src/i18n/messages/en.json", ["Net profit", "Advertising spend", "Meta Ads API is not active", "operational profit analytics"]],
  ["backend/app/services/finance_service.py", ["VALID_REVENUE_STATUSES", "advertising_manual_csv_source", "meta_ads_not_active", "missing_product_cost", "missing_shipment_cost"]],
  ["backend/app/api/v1/finance.py", ["/summary", "require_min_role(RoleName.ANALYST)"]],
  ["docs/finance-metrics.md", ["Finance uses Advertising data only as conditional manual/CSV source", "Meta Ads API is not active", "not full accounting software", "NaN", "Infinity"]],
  ["docs/finance-part-5-plan.md", ["Finance Part 5", "manual/CSV", "Meta Ads API is not active"]],
  ["docs/finance-part-5-handoff.md", ["Epic Sprint 5A", "conditional manual/CSV source"]],
  ["docs/advertising-known-blockers.md", ["Advertising remains feature-frozen", "not pilot-ready"]],
];

const forbidden = [
  ["backend/app/services/finance_service.py", ["facebook.com", "graph.facebook.com", "httpx", "requests", ".commit(", ".flush("]],
  ["frontend/src/app/finance/page.tsx", ["pilot-ready", "access_token", "client_secret"]],
];

let failed = false;
for (const [file, markers] of checks) {
  const source = readFileSync(file, "utf8");
  for (const marker of markers) {
    if (!source.includes(marker)) {
      console.error(`Missing marker in ${file}: ${marker}`);
      failed = true;
    }
  }
}
for (const [file, markers] of forbidden) {
  const source = readFileSync(file, "utf8");
  for (const marker of markers) {
    if (source.includes(marker)) {
      console.error(`Forbidden marker in ${file}: ${marker}`);
      failed = true;
    }
  }
}
if (failed) process.exit(1);
console.log("finance foundation regression passed");
