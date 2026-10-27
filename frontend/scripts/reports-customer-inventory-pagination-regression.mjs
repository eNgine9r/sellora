import { readFileSync } from "node:fs";

const read = (path) => readFileSync(path, "utf8");
const report = read("frontend/src/app/analytics/page.tsx");
const pager = read("frontend/src/components/pagination-controls.tsx");
const checks = [
  ["shared paginator is used for all three report tables", (report.match(/<PaginationControls /g) ?? []).length === 3],
  ["report pagination uses the existing 5/15/30 choices", pager.includes("PAGE_SIZE_OPTIONS = [5, 15, 30]")],
  ["customer report no longer truncates the data to eight entries", !report.includes("(customers.data ?? []).slice(0, 8)") && report.includes("rows={paginatedCustomerRows}")],
  ["stock report renders paginated low-stock entries", report.includes("rows={paginatedInventoryRows}")],
  ["customer page is independent of sales and inventory", report.includes("const [customersPage, setCustomersPage] = useState(1)") && report.includes("const [customersPageSize, setCustomersPageSize]")],
  ["inventory page is independent of sales and customers", report.includes("const [inventoryPage, setInventoryPage] = useState(1)") && report.includes("const [inventoryPageSize, setInventoryPageSize]")],
  ["customer pager counts all records, not only current page", report.includes("totalItems={customerRows.length}") && report.includes("paginateItems(customerRows, customersPage, customersPageSize)")],
  ["stock pager counts all records, not only current page", report.includes("totalItems={inventoryRows.length}") && report.includes("paginateItems(inventoryRows, inventoryPage, inventoryPageSize)")],
  ["customer page resets on workspace, date range and size", report.includes("setCustomersPage(1);\n  }, [workspaceId, startDate, endDate, customersPageSize]")],
  ["inventory page resets on workspace, date range and size", report.includes("setInventoryPage(1);\n  }, [workspaceId, startDate, endDate, inventoryPageSize]")],
  ["customer page clamps when result count shrinks", report.includes("clampPage(page, customersPageSize, customerRows.length)")],
  ["inventory page clamps when result count shrinks", report.includes("clampPage(page, inventoryPageSize, inventoryRows.length)")],
  ["mobile cards remain adaptive", report.includes("analytics-pagination-section grid min-w-0 gap-3") && report.includes("<ResponsiveReportTable")],
  ["existing sales report pagination retained", report.includes("rows={paginatedSalesRows}") && report.includes("totalItems={salesRows.length}")],
  ["all pagination controls are localized", pager.includes('t("pagination.showing")') && pager.includes('t("pagination.previous")') && pager.includes('t("pagination.next")')],
];

const failed = checks.filter(([, ok]) => !ok);
for (const [label, ok] of checks) console.log(`${ok ? "✓" : "✗"} ${label}`);
if (failed.length) {
  console.error(`Report customer/inventory pagination regression failed: ${failed.map(([label]) => label).join(", ")}`);
  process.exit(1);
}
console.log(`Report customer/inventory pagination PASS (${checks.length} checks)`);
