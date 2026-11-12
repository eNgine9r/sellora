import { readFileSync } from "node:fs";

const source = (path) => readFileSync(path, "utf8");
const page = source("frontend/src/app/shipments/page.tsx");
const np = source("frontend/src/features/shipments/components/nova-poshta-external-inbox.tsx");
const failures = [];
const requireMarker = (content, needle) => { if (!content.includes(needle)) failures.push(`Missing ${needle}`); };

[
  "data-shipments-compact-summary", "md:grid-cols-4", "min-h-[72px]",
  "data-shipments-compact-filters", "showAdvancedFilters",
  "aria-expanded={showAdvancedFilters}", 'aria-controls="shipments-advanced-filters"',
  "data-shipments-advanced-filters", "setShowAdvancedFilters((expanded) => !expanded)",
  "setCarrier(event.target.value", "setTtnFilter(event.target.value",
  "setShipmentSort", "advancedFilterCount", "hasActiveFilters",
  "const resetFilters = () =>", "setPage(1)",
  'queryKey: ["shipments", workspaceId, "", ""]',
  "const allShipments = overview.length", "const hasAnyShipments = (overviewQuery.data?.length",
  "overviewQuery.isPending", "summaryQuery.data?.in_transit_count",
  "t(\"shipments.summary.ready\")", "t(\"shipments.summary.delivered\")",
  "<ShipmentTable", "<PaginationControls", "shipments-pagination-section",
].forEach(marker => requireMarker(page, marker));

[
  'if (mode === "summary")', 'data-smart-sale-queue-mode="summary"',
  "data-sale-queue-counts", 'href="/shipments/confirmations"',
  "scan.mutate()", "getSmartSaleCandidates(workspaceId)",
].forEach(marker => requireMarker(np, marker));

const summary = page.substring(page.indexOf("data-shipments-compact-summary"), page.indexOf("data-shipments-compact-filters"));
if (summary.includes("five-balanced")) failures.push("Old five balanced oversized KPI grid used");
if (page.includes("<FilterBar>")) failures.push("Expanded shared FilterBar remains in Shipments");
if (page.includes("<ResetFiltersButton")) failures.push("Persistent full-size reset button remains");
if (summary.includes("problemShipments")) failures.push("Misleading duplicate 'ready vs problems' KPI remains");
if (np.includes('className="grid grid-cols-2 gap-2 lg:grid-cols-4" data-sale-queue-counts') === false) failures.push("Full confirmation view lost its 4-card statistics");
if (!np.includes("if (mode === \"summary\")")) failures.push("Summary not a compact distinct path");

if (failures.length) {
  console.error("SHIPMENTS_COMPACT_FILTERS_REGRESSION_FAILED\n" + failures.join("\n"));
  process.exit(1);
}
console.log("SHIPMENTS_COMPACT_FILTERS_REGRESSION_PASS");
