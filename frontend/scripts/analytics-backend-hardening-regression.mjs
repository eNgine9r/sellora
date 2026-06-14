import { readFileSync } from "node:fs";

const files = {
  backendRoutes: readFileSync("backend/app/api/v1/analytics.py", "utf8"),
  backendService: readFileSync("backend/app/services/analytics_service.py", "utf8"),
  backendRepo: readFileSync("backend/app/repositories/analytics_repository.py", "utf8"),
  frontendServices: readFileSync("frontend/src/services/analytics.ts", "utf8"),
  dashboard: readFileSync("frontend/src/app/dashboard/page.tsx", "utf8"),
  analytics: readFileSync("frontend/src/app/analytics/page.tsx", "utf8"),
  packageJson: readFileSync("frontend/package.json", "utf8"),
  docs: readFileSync("docs/analytics-metrics.md", "utf8"),
};

const checks = [
  ["sales report backend endpoint", files.backendRoutes.includes('/sales-report') && files.backendService.includes('def sales_report')],
  ["products report backend endpoint", files.backendRoutes.includes('/products-report') && files.backendService.includes('def products_report')],
  ["advertising report backend endpoint", files.backendRoutes.includes('/advertising-report') && files.backendService.includes('def advertising_report')],
  ["customers report backend endpoint", files.backendRoutes.includes('/customers-report') && files.backendService.includes('def customers_report')],
  ["inventory report backend endpoint", files.backendRoutes.includes('/inventory-report') && files.backendService.includes('def inventory_report')],
  ["business insights backend endpoint", files.backendRoutes.includes('/business-insights') && files.backendService.includes('def business_insights')],
  ["dashboard summary endpoint", files.backendRoutes.includes('/dashboard-summary') && files.frontendServices.includes('fetchDashboardSummary')],
  ["repository workspace scoped analytics", files.backendRepo.includes('workspace_id == workspace_id') && files.backendRepo.includes('deleted_at.is_(None)')],
  ["RBAC profit hardening marker", files.backendService.includes('can_view_profit') && files.backendRoutes.includes('_can_view_profit')],
  ["zero denominator safe null marker", files.backendService.includes('_safe_divide') && files.backendService.includes('return None')],
  ["frontend sales report endpoint usage", files.analytics.includes('fetchSalesReport')],
  ["frontend product report endpoint usage", files.analytics.includes('fetchProductsReport')],
  ["frontend dashboard backend aggregate usage", files.dashboard.includes('fetchDashboardSummary') && files.dashboard.includes('backendDashboard')],
  ["typecheck script exists", files.packageJson.includes('"typecheck": "tsc --noEmit"')],
  ["docs mention Sprint 2.5 backend aggregation", files.docs.includes('Sprint 2.5') && files.docs.includes('/api/v1/analytics/sales-report')],
];

const failed = checks.filter(([, ok]) => !ok);
if (failed.length) {
  console.error(`Analytics backend hardening regression failed: ${failed.map(([name]) => name).join(', ')}`);
  process.exit(1);
}
console.log(`Analytics backend hardening regression passed (${checks.length} checks).`);
