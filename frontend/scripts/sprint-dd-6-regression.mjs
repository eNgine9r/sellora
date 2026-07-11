import { readFileSync } from "node:fs";
const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), "utf8");
const checks = [];
const check = (name, ok) => checks.push({ name, ok });
const advertising = read("src/app/advertising/page.tsx");
const finance = read("src/app/finance/page.tsx");
const analytics = read("src/app/analytics/page.tsx");
const campaignTable = read("src/features/advertising/components/campaign-table.tsx");
const period = read("src/features/advertising/components/advertising-date-range-filter.tsx");

for (const [name, source] of [["advertising", advertising], ["finance", finance], ["analytics", analytics]]) {
  check(`${name} uses WorkspacePage`, source.includes("<WorkspacePage>"));
  check(`${name} uses WorkspaceHeader`, source.includes("<WorkspaceHeader"));
  check(`${name} avoids centered max-width shell`, !source.includes("max-w-7xl") && !source.includes("bg-[#F8F7FC]"));
  check(`${name} uses semantic surfaces`, source.includes("bg-surface") || source.includes("CompactSummary"));
}
check("Advertising has explicit five-card summary", advertising.includes('CompactSummary layout="five-balanced"'));
check("Finance has explicit five-card summary", finance.includes('CompactSummary layout="five-balanced"'));
check("Analytics has explicit five-card summary", analytics.includes('CompactSummary layout="five-balanced"'));
check("Advertising uses one period selector", (advertising.match(/AdvertisingDateRangeFilter/g) ?? []).length === 2 && period.includes('data-period-selector="advertising"'));
check("Finance uses one period filter", (finance.match(/data-finance-period-filter/g) ?? []).length === 1);
check("Analytics uses one DateRangeSelector", (analytics.match(/DateRangeSelector/g) ?? []).length === 2);
check("Advertising campaign details use split view", advertising.includes("<WorkspaceSplitView") && advertising.includes("<EntitySidePanel"));
check("Campaign table has selected state", campaignTable.includes("selectedCampaignId") && campaignTable.includes("bg-surface-selected"));
check("Advertising paginates below tables", advertising.indexOf("<CampaignPerformanceTable") < advertising.indexOf("<PaginationControls page={performancePage}") && advertising.indexOf("<AdMetricTable") < advertising.indexOf("<PaginationControls page={metricPage}") && advertising.indexOf("<CampaignTable") < advertising.indexOf("<PaginationControls page={campaignPage}"));
check("Finance adjustment pagination is below rows", finance.indexOf("paginatedAdjustments.map") < finance.indexOf("<PaginationControls page={adjustmentPage}"));
check("Analytics sales pagination is below sales table", analytics.indexOf("<TableShell><table") < analytics.indexOf("<PaginationControls page={analyticsPage}"));
check("Unavailable values remain distinct", advertising.includes('?? "—"') && analytics.includes("UNAVAILABLE") && finance.includes('value: summary.average_order_value ?'));
check("Advertising does not claim live Meta sync", !advertising.toLowerCase().includes("live sync") && !advertising.toLowerCase().includes("connected meta"));
check("Finance displays expense components", finance.includes("summary.cogs") && finance.includes("summary.ad_spend") && finance.includes("summary.shipping_cost") && finance.includes("summary.finance_adjustments_total"));
check("Analytics is not dashboard clone", analytics.includes("analytics.products.title") && analytics.includes("analytics.customers.title") && analytics.includes("analytics.inventory.title"));

const failed = checks.filter((item) => !item.ok);
if (failed.length) {
  console.error("Sprint Dd.6 regression failed:");
  for (const item of failed) console.error(`- ${item.name}`);
  process.exit(1);
}
console.log(`Sprint Dd.6 regression passed (${checks.length} checks).`);
