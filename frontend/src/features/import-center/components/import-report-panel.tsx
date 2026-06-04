import { ImportReport } from "@/types/import-center";

export function ImportReportPanel({ report }: { report?: ImportReport }) {
  if (!report) return null;
  const catalogMetrics = ([
    ["Products", report.products_detected], ["Variants", report.variants_detected], ["Inventory rows", report.inventory_rows_detected], ["Images", report.images_detected], ["Duplicate products", report.duplicate_products], ["Duplicate variants", report.duplicate_variants],
  ] as [string, unknown][]).filter(([, value]) => typeof value === "number" && value > 0);
  const orderMetrics = ([
    ["Orders detected", report.orders_detected], ["Order items detected", report.order_items_detected], ["Customers matched", report.customers_matched], ["Customers to create", report.customers_to_create], ["Variants matched", report.variants_matched], ["Variants missing", report.variants_missing], ["Shipments detected", report.shipments_detected], ["Duplicate orders", report.duplicate_orders], ["Ready orders", report.ready_orders], ["Ready items", report.ready_items], ["Estimated revenue", report.estimated_revenue], ["Estimated ad cost", report.estimated_ad_cost], ["Estimated profit", report.estimated_profit],
  ] as [string, unknown][]).filter(([, value]) => value !== undefined && value !== null && value !== 0 && value !== "0");
  const adMetrics = ([
    ["Campaigns detected", report.campaigns_detected], ["Campaigns to create", report.campaigns_to_create], ["Campaigns reused", report.campaigns_reused], ["Metrics detected", report.metrics_detected], ["Duplicate metrics", report.duplicate_metrics], ["Estimated spend", report.estimated_spend], ["Estimated revenue", report.estimated_revenue], ["Estimated net profit", report.estimated_net_profit], ["Estimated ROAS", report.estimated_roas],
  ] as [string, unknown][]).filter(([, value]) => value !== undefined && value !== null && value !== 0 && value !== "0");
  return <section className="rounded-xl bg-white p-4 shadow-sm"><h2 className="font-semibold">Dry run report</h2><div className="mt-3 grid gap-2 text-sm md:grid-cols-4"><span>Total {report.total_rows}</span><span>Ready {report.ready_to_import_rows}</span><span>Warnings {report.warning_rows}</span><span>Errors {report.error_rows}</span><span>Duplicates {report.duplicate_rows}</span><span>Skipped {report.skipped_rows}</span><span>Estimate {report.estimated_entities_to_create}</span></div>{catalogMetrics.length ? <MetricBlock title="Product catalog counters" tone="blue" metrics={catalogMetrics} /> : null}{orderMetrics.length ? <MetricBlock title="Historical orders counters" tone="amber" metrics={orderMetrics} /> : null}{adMetrics.length ? <MetricBlock title="Historical advertising counters" tone="purple" metrics={adMetrics} /> : null}<div className="mt-4 grid gap-4 md:grid-cols-2"><div><h3 className="font-medium text-red-600">Sample errors</h3>{report.sample_errors.map((item, index) => <p className="text-sm" key={index}>Row {item.row_number}: {item.message}</p>)}</div><div><h3 className="font-medium text-amber-600">Sample warnings</h3>{report.sample_warnings.map((item, index) => <p className="text-sm" key={index}>Row {item.row_number}: {item.message}</p>)}</div></div></section>;
}

function MetricBlock({ title, tone, metrics }: { title: string; tone: "blue" | "amber" | "purple"; metrics: [string, unknown][] }) {
  const color = tone === "blue" ? "bg-blue-50 text-blue-700" : tone === "amber" ? "bg-amber-50 text-amber-800" : "bg-purple-50 text-purple-800";
  return <div className={`mt-4 rounded-lg p-3 ${color}`}><h3 className="font-medium">{title}</h3><div className="mt-2 grid gap-2 text-sm md:grid-cols-3">{metrics.map(([label, value]) => <span key={label}>{label}: {String(value)}</span>)}</div></div>;
}
