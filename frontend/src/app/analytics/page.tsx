"use client";

import Link from "next/link";
import { DateRangeSelector } from "@/components/date-range-selector";
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/states";
import { ResponsiveReportTable } from "@/components/ui/responsive-report-table";
import { clampPage, paginateItems, PaginationControls, PAGE_SIZE_OPTIONS } from "@/components/pagination-controls";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { ANALYTICS_ORDER_STATUSES, ANALYTICS_PAYMENT_STATUSES, buildBusinessInsights, buildDailySalesRows, buildVariantLookups, formatDecimal, formatPercentValue, leadsInRange, ordersInRange, summarizeAdvertising, safeDivide, summarizeCustomers, summarizeInventory, summarizeOrders, toFiniteNumber, UNAVAILABLE } from "@/lib/analytics-formulas";
import { displayCategory } from "@/lib/categories";
import { formatMoney } from "@/lib/currency";
import { useDateRange } from "@/providers/date-range-provider";
import { fetchAdvertisingSummary, fetchCampaignPerformance, fetchAdvertisingTrend } from "@/services/advertising";
import { fetchAdvertisingReport, fetchBusinessInsights, fetchCustomersSummary, fetchInventoryReport, fetchInventorySummary, fetchProfitSummary, fetchSalesReport, fetchSalesSummary, fetchTopProducts } from "@/services/analytics";
import { fetchCustomers, fetchLeads } from "@/services/crm";
import { fetchOrders } from "@/services/orders";
import { fetchInventory, fetchProducts, fetchProductVariants } from "@/services/products";
import { CompactSummary, WorkspaceHeader, WorkspacePage } from "@/components/crm-workspace";

function ReportCard({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return <section className="min-w-0 overflow-hidden rounded-[24px] border border-border-subtle bg-surface-1 p-4 shadow-[var(--shadow-card)] sm:p-5"><div className="mb-4 min-w-0"><h2 className="break-words text-xl font-black text-text-primary">{title}</h2>{subtitle ? <p className="mt-1 break-words text-sm text-text-muted">{subtitle}</p> : null}</div>{children}</section>;
}

function MetricCard({ label, value, helper }: { label: string; value: string | number; helper?: string }) {
  return <article className="min-w-0 rounded-2xl border border-border-subtle bg-surface-2 p-4 "><p className="break-words text-xs font-black uppercase tracking-[0.18em] text-text-muted">{label}</p><p className="mt-2 break-words text-2xl font-black text-text-primary">{value}</p>{helper ? <p className="mt-1 break-words text-xs font-semibold text-text-muted">{helper}</p> : null}</article>;
}

export default function AnalyticsPage() {
  const { t, formatStatus } = useI18n();
  const { range } = useDateRange();
  const { currentUser, currentWorkspace, currentWorkspaceId, status: authStatus } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const currencyCode = currentWorkspace?.currency_code ?? "UAH";
  const canSeeProfit = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "ANALYST";
  const enabled = authStatus === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);
  const startDate = range.date_from || undefined;
  const endDate = range.date_to || undefined;
  const [analyticsPage, setAnalyticsPage] = useState(1);
  const [analyticsPageSize, setAnalyticsPageSize] = useState<(typeof PAGE_SIZE_OPTIONS)[number]>(5);

  const salesReport = useQuery({ queryKey: ["analytics-sales-report", workspaceId, startDate, endDate], queryFn: () => fetchSalesReport(workspaceId, undefined, startDate, endDate), enabled });
  const advertisingReport = useQuery({ queryKey: ["analytics-advertising-report", workspaceId, startDate, endDate], queryFn: () => fetchAdvertisingReport(workspaceId, undefined, startDate, endDate), enabled });
  const inventoryReport = useQuery({ queryKey: ["analytics-inventory-report", workspaceId, startDate, endDate], queryFn: () => fetchInventoryReport(workspaceId, undefined, startDate, endDate), enabled });
  const backendInsights = useQuery({ queryKey: ["analytics-business-insights", workspaceId, startDate, endDate], queryFn: () => fetchBusinessInsights(workspaceId, undefined, startDate, endDate), enabled });
  const sales = useQuery({ queryKey: ["analytics-sales", workspaceId, startDate, endDate], queryFn: () => fetchSalesSummary(workspaceId, undefined, startDate, endDate), enabled });
  const profit = useQuery({ queryKey: ["analytics-profit", workspaceId, startDate, endDate], queryFn: () => fetchProfitSummary(workspaceId, undefined, startDate, endDate), enabled: enabled && canSeeProfit });
  const topProducts = useQuery({ queryKey: ["analytics-products", workspaceId, startDate, endDate], queryFn: () => fetchTopProducts(workspaceId, undefined, startDate, endDate, 12), enabled: enabled && canSeeProfit });
  const customersSummary = useQuery({ queryKey: ["analytics-customers-summary", workspaceId, startDate, endDate], queryFn: () => fetchCustomersSummary(workspaceId, undefined, startDate, endDate), enabled });
  const inventorySummary = useQuery({ queryKey: ["analytics-inventory-summary", workspaceId], queryFn: () => fetchInventorySummary(workspaceId, undefined), enabled });
  const advertising = useQuery({ queryKey: ["analytics-advertising-summary", workspaceId, startDate, endDate], queryFn: () => fetchAdvertisingSummary(workspaceId, undefined, startDate, endDate), enabled });
  const campaignPerformance = useQuery({ queryKey: ["analytics-campaign-performance", workspaceId, startDate, endDate], queryFn: () => fetchCampaignPerformance(workspaceId, undefined, startDate, endDate, 12), enabled });
  const advertisingTrend = useQuery({ queryKey: ["analytics-advertising-trend", workspaceId, startDate, endDate], queryFn: () => fetchAdvertisingTrend(workspaceId, undefined, startDate, endDate), enabled });
  const orders = useQuery({ queryKey: ["analytics-orders", workspaceId], queryFn: () => fetchOrders(workspaceId, ""), enabled });
  const leads = useQuery({ queryKey: ["analytics-leads", workspaceId], queryFn: () => fetchLeads(workspaceId, {}), enabled });
  const customers = useQuery({ queryKey: ["analytics-customers", workspaceId], queryFn: () => fetchCustomers(workspaceId), enabled });
  const products = useQuery({ queryKey: ["analytics-product-catalog", workspaceId], queryFn: () => fetchProducts(workspaceId), enabled });
  const variants = useQuery({ queryKey: ["analytics-variants", workspaceId], queryFn: () => fetchProductVariants(workspaceId, undefined, undefined), enabled });
  const inventory = useQuery({ queryKey: ["analytics-inventory", workspaceId], queryFn: () => fetchInventory(workspaceId), enabled });

  const currentOrders = useMemo(() => ordersInRange(orders.data ?? [], range), [orders.data, range]);
  const currentLeads = useMemo(() => leadsInRange(leads.data ?? [], range), [leads.data, range]);
  const orderSummary = useMemo(() => summarizeOrders(currentOrders), [currentOrders]);
  const salesRows = useMemo(() => buildDailySalesRows(currentOrders), [currentOrders]);
  const paginatedSalesRows = useMemo(() => paginateItems(salesRows, analyticsPage, analyticsPageSize), [analyticsPage, analyticsPageSize, salesRows]);
  const backendAdSummary = advertisingReport.data;
  const adSummary = useMemo(() => summarizeAdvertising(advertising.data), [advertising.data]);
  const customerSummary = useMemo(() => summarizeCustomers(customers.data ?? []), [customers.data]);
  const inventoryRollup = useMemo(() => summarizeInventory(inventory.data ?? []), [inventory.data]);
  const leadConversionRate = safeDivide(currentLeads.filter((lead) => lead.status === "CONVERTED").length * 100, currentLeads.length);
  const lookups = useMemo(() => buildVariantLookups(products.data ?? [], variants.data ?? [], inventory.data ?? []), [products.data, variants.data, inventory.data]);
  const insights = useMemo(() => buildBusinessInsights({ orders: currentOrders, adSummary: advertising.data, inventory: inventory.data ?? [], products: products.data ?? [], variants: variants.data ?? [], leads: currentLeads }), [advertising.data, currentLeads, currentOrders, inventory.data, products.data, variants.data]);
  const backendInsightRows = backendInsights.data?.insights ?? [];

  const productRows = useMemo(() => (topProducts.data ?? []).map((item) => {
    const product = lookups.productById.get(item.product_id);
    const stock = lookups.inventoryByVariantId.get(item.variant_id);
    return { ...item, category: displayCategory(product?.category, t), stockQuantity: stock?.stock_quantity ?? 0, reservedQuantity: stock?.reserved_quantity ?? 0, status: stock && stock.stock_quantity <= stock.minimum_quantity ? t("analytics.inventory.lowStockStatus") : t("analytics.inventory.healthyStatus") };
  }), [lookups, t, topProducts.data]);

  const topCategories = useMemo(() => {
    const grouped = new Map<string, { category: string; quantity: number; revenue: number; netProfit: number }>();
    for (const order of currentOrders) for (const item of order.items) {
      const variant = lookups.variantById.get(item.product_variant_id);
      const product = variant ? lookups.productById.get(variant.product_id) : undefined;
      const category = displayCategory(product?.category, t);
      const row = grouped.get(category) ?? { category, quantity: 0, revenue: 0, netProfit: 0 };
      row.quantity += item.quantity;
      if (["NEW", "CONFIRMED", "SHIPPED", "DELIVERED", "COMPLETED"].includes(order.status)) {
        row.revenue += toFiniteNumber(item.line_total);
        row.netProfit += toFiniteNumber(item.line_total) - toFiniteNumber(item.line_cost);
      }
      grouped.set(category, row);
    }
    const totalRevenue = Array.from(grouped.values()).reduce((sum, row) => sum + row.revenue, 0);
    return Array.from(grouped.values()).sort((a, b) => b.revenue - a.revenue).slice(0, 6).map((row) => ({ ...row, share: formatPercentValue(totalRevenue ? (row.revenue / totalRevenue) * 100 : null) }));
  }, [currentOrders, lookups.productById, lookups.variantById, t]);

  const isLoading = sales.isLoading || advertising.isLoading || orders.isLoading || leads.isLoading || customers.isLoading || inventory.isLoading || products.isLoading || variants.isLoading;
  const hasError = sales.isError || advertising.isError || orders.isError || leads.isError || customers.isError || inventory.isError || products.isError || variants.isError;

  useEffect(() => {
    setAnalyticsPage(1);
  }, [startDate, endDate, analyticsPageSize]);

  useEffect(() => {
    setAnalyticsPage((currentPage) => clampPage(currentPage, analyticsPageSize, salesRows.length));
  }, [analyticsPageSize, salesRows.length]);

  return (
    <WorkspacePage>
        <WorkspaceHeader title={t("analytics.reports.title")} description={t("analytics.reports.subtitle")} eyebrow={t("analytics.reports.eyebrow")} />

        {hasError ? <ErrorState description={t("analytics.errors.loadFailed")} /> : null}
        {isLoading ? <div className="grid gap-4 md:grid-cols-3"><LoadingSkeleton title={t("analytics.reports.loading")} rows={3} /><LoadingSkeleton title={t("analytics.sales.title")} rows={3} /><LoadingSkeleton title={t("analytics.insights.title")} rows={3} /></div> : null}

        <div className="grid gap-2 rounded-3xl border border-slate-100 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-slate-900 md:grid-cols-[1fr_auto] md:items-center">
          <div><h2 className="font-black text-text-primary">{t("analytics.filters.period")}</h2><p className="text-sm text-text-muted">{t("analytics.filters.periodHelp")}</p></div>
          <div className="rounded-3xl bg-slate-50 p-2 dark:bg-white/5"><DateRangeSelector compact /></div>
        </div>

        <CompactSummary layout="five-balanced" items={[{ label: t("analytics.metrics.orders"), value: orderSummary.ordersCount }, { label: t("analytics.metrics.revenue"), value: formatMoney(toFiniteNumber(salesReport.data?.revenue ?? orderSummary.revenue), currencyCode) }, { label: t("analytics.metrics.netProfit"), value: (salesReport.data?.can_view_profit ?? canSeeProfit) ? formatMoney(toFiniteNumber(salesReport.data?.net_profit ?? profit.data?.total_net_profit ?? orderSummary.netProfit), currencyCode) : t("analytics.metrics.restricted") }, { label: t("analytics.metrics.aov"), value: (salesReport.data?.aov ?? orderSummary.aov) == null ? UNAVAILABLE : formatMoney(toFiniteNumber(salesReport.data?.aov ?? orderSummary.aov), currencyCode), unavailable: (salesReport.data?.aov ?? orderSummary.aov) == null }, { label: t("analytics.metrics.repeatCustomerRate"), value: formatPercentValue(customerSummary.repeatCustomerRate), helper: t("analytics.tooltips.repeatCustomerRate") }]} />

        <ReportCard title={t("analytics.insights.title")} subtitle={t("analytics.insights.subtitle")}>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {(backendInsightRows.length ? backendInsightRows.map((insight) => ({ type: insight.type, titleKey: insight.title_key, descriptionKey: insight.description_key, sourceMetric: insight.source_metric, href: insight.route ?? undefined, ctaKey: insight.cta_key ?? undefined, values: insight.value == null ? undefined : { value: insight.value } })) : insights).map((insight) => <Link key={`${insight.sourceMetric}-${insight.titleKey}`} href={insight.href ?? "/analytics"} className="rounded-2xl border border-border-subtle bg-surface-2 p-4 transition hover:-translate-y-0.5 hover:border-violet-200 hover:bg-violet-50  dark:hover:bg-violet-400/10"><span className="text-xs font-black uppercase tracking-[0.18em] text-violet-600 dark:text-violet-200">{t(`analytics.insights.types.${insight.type}`)} · {insight.sourceMetric}</span><h3 className="mt-2 font-black text-text-primary">{t(insight.titleKey, insight.values)}</h3><p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{t(insight.descriptionKey, insight.values)}</p>{insight.ctaKey ? <p className="mt-3 text-sm font-bold text-violet-700 dark:text-violet-200">{t(insight.ctaKey)}</p> : null}</Link>)}
          </div>
        </ReportCard>

        <ReportCard title={t("analytics.sales.title")} subtitle={t("analytics.sales.subtitle")}>
          <div className="mb-4 grid gap-3 md:grid-cols-4"><MetricCard label={t("analytics.metrics.revenue")} value={formatMoney(toFiniteNumber(salesReport.data?.revenue ?? orderSummary.revenue), currencyCode)} helper={t("analytics.tooltips.revenue")} /><MetricCard label={t("analytics.metrics.netProfit")} value={(salesReport.data?.can_view_profit ?? canSeeProfit) ? formatMoney(toFiniteNumber(salesReport.data?.net_profit ?? profit.data?.total_net_profit ?? orderSummary.netProfit), currencyCode) : t("analytics.metrics.restricted")} helper={t("analytics.tooltips.netProfit")} /><MetricCard label={t("analytics.metrics.aov")} value={(salesReport.data?.aov ?? orderSummary.aov) == null ? UNAVAILABLE : formatMoney(toFiniteNumber(salesReport.data?.aov ?? orderSummary.aov), currencyCode)} helper={t("analytics.tooltips.aov")} /><MetricCard label={t("analytics.metrics.returnRate")} value={formatPercentValue(toFiniteNumber(salesReport.data?.return_rate ?? orderSummary.returnRate))} helper={t("analytics.tooltips.returnRate")} /></div>
          <div className="mb-4 grid gap-3 md:grid-cols-4"><MetricCard label={t("analytics.metrics.orders")} value={orderSummary.ordersCount} /><MetricCard label={t("analytics.metrics.margin")} value={canSeeProfit ? formatPercentValue(orderSummary.margin) : t("analytics.metrics.restricted")} helper={t("analytics.tooltips.margin")} /><MetricCard label={t("analytics.metrics.cancelledOrders")} value={orderSummary.cancelledOrders} /><MetricCard label={t("analytics.metrics.deliveredOrders")} value={orderSummary.deliveredOrders} /></div>
          <div className="analytics-pagination-section grid gap-3">
            <ResponsiveReportTable
  rows={paginatedSalesRows}
  rowKey={(row) => row.date}
  columns={[
    { key: "date", label: t("analytics.tables.date"), render: (row) => row.date ,emphasis: true },
    { key: "orders", label: t("analytics.tables.orders"), render: (row) => row.orders },
    { key: "revenue", label: t("analytics.tables.revenue"), render: (row) => formatMoney(row.revenue, currencyCode) },
    ...(canSeeProfit ? [{key: "profit", label: t("analytics.tables.netProfit"), render: (row: (typeof paginatedSalesRows)[number]) => formatMoney(row.netProfit, currencyCode)}] : []),
    { key: "aov", label: t("analytics.tables.aov"), render: (row) => row.aov == null ? UNAVAILABLE : formatMoney(row.aov, currencyCode) },
    { key: "returns", label: t("analytics.tables.returns"), render: (row) => row.returns },
    { key: "cancelled", label: t("analytics.tables.cancelled"), render: (row) => row.cancelled },
  ]}
  empty={<EmptyState title={t("analytics.emptyStates.noSales")} description={t("analytics.emptyStates.noSalesDescription")} />}
  wide
/>{salesRows.length > 0 ? <PaginationControls page={analyticsPage} pageSize={analyticsPageSize} totalItems={salesRows.length} onPageChange={setAnalyticsPage} onPageSizeChange={(nextPageSize) => setAnalyticsPageSize(nextPageSize as (typeof PAGE_SIZE_OPTIONS)[number])} /> : null}
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2"><div className="rounded-2xl bg-slate-50 p-4 dark:bg-white/[0.05]"><h3 className="font-black dark:text-white">{t("analytics.sales.byStatus")}</h3><div className="mt-3 grid gap-2">{ANALYTICS_ORDER_STATUSES.map((status) => <div key={status} className="flex justify-between text-sm"><span>{formatStatus("order", status)}</span><strong>{orderSummary.statusCounts[status]}</strong></div>)}</div></div><div className="rounded-2xl bg-slate-50 p-4 dark:bg-white/[0.05]"><h3 className="font-black dark:text-white">{t("analytics.sales.byPayment")}</h3><div className="mt-3 grid gap-2">{ANALYTICS_PAYMENT_STATUSES.map((status) => <div key={status} className="flex justify-between text-sm"><span>{formatStatus("payment", status)}</span><strong>{orderSummary.paymentCounts[status]}</strong></div>)}</div></div></div>
        </ReportCard>

        <ReportCard title={t("analytics.products.title")} subtitle={t("analytics.products.subtitle")}>
          <div className="mb-4 grid gap-3 md:grid-cols-3"><MetricCard label={t("analytics.products.topByRevenue")} value={productRows[0]?.product_name ?? UNAVAILABLE} /><MetricCard label={t("analytics.products.lowStockBestSellers")} value={productRows.filter((row) => row.stockQuantity <= 0 || row.status === t("analytics.inventory.lowStockStatus")).length} /><MetricCard label={t("analytics.products.categoriesTracked")} value={topCategories.length} /></div>
          <ResponsiveReportTable
  rows={productRows}
  rowKey={(row) => row.variant_id}
  columns={[
    { key: "product", label: t("analytics.tables.product"), render: (row) => row.product_name ,emphasis: true },
    { key: "sku", label: t("analytics.tables.sku"), render: (row) => row.variant_sku },
    { key: "category", label: t("analytics.tables.category"), render: (row) => row.category },
    { key: "qty", label: t("analytics.tables.quantitySold"), render: (row) => row.quantity_sold },
    { key: "revenue", label: t("analytics.tables.revenue"), render: (row) => formatMoney(row.revenue, currencyCode) },
    ...(canSeeProfit ? [{key: "profit", label: t("analytics.tables.netProfit"), render: (row: (typeof productRows)[number]) => formatMoney(row.net_profit, currencyCode)}] : []),
    { key: "stock", label: t("analytics.tables.stock"), render: (row) => row.stockQuantity },
    { key: "reserved", label: t("analytics.tables.reserved"), render: (row) => row.reservedQuantity },
    { key: "status", label: t("analytics.tables.status"), render: (row) => row.status },
  ]}
  empty={<EmptyState title={t("analytics.emptyStates.noProducts")} description={t("analytics.emptyStates.noProductsDescription")} />}
  wide
/>
          <div className="mt-4 grid gap-3 md:grid-cols-2">{topCategories.map((row) => <div key={row.category} className="rounded-2xl bg-slate-50 p-4 dark:bg-white/[0.05]"><h3 className="font-black text-text-primary">{row.category}</h3><p className="text-sm text-text-muted">{row.quantity} {t("analytics.products.unitsSold")} · {formatMoney(row.revenue, currencyCode)} · {row.share}</p></div>)}</div>
        </ReportCard>

        <ReportCard title={t("analytics.advertising.title")} subtitle={t("analytics.advertising.subtitle")}>
          <div className="mb-4 grid gap-3 md:grid-cols-4"><MetricCard label={t("analytics.metrics.spend")} value={formatMoney(toFiniteNumber(backendAdSummary?.spend ?? adSummary.spend), currencyCode)} /><MetricCard label={t("analytics.metrics.roas")} value={formatDecimal(adSummary.roas)} helper={t("analytics.tooltips.roas")} /><MetricCard label={t("analytics.metrics.cpa")} value={(backendAdSummary?.cpa ?? adSummary.cpa) == null ? UNAVAILABLE : formatMoney(toFiniteNumber(backendAdSummary?.cpa ?? adSummary.cpa), currencyCode)} helper={t("analytics.tooltips.cpa")} /><MetricCard label={t("analytics.metrics.cpl")} value={(backendAdSummary?.cpl ?? adSummary.cpl) == null ? UNAVAILABLE : formatMoney(toFiniteNumber(backendAdSummary?.cpl ?? adSummary.cpl), currencyCode)} helper={t("analytics.tooltips.cpl")} /></div>
          <ResponsiveReportTable
  rows={campaignPerformance.data ?? []}
  rowKey={(row) => row.campaign_id}
  columns={[
    { key: "campaign", label: t("analytics.tables.campaign"), render: (row) => row.campaign_name ,emphasis: true },
    { key: "platform", label: t("analytics.tables.platform"), render: (row) => row.platform },
    { key: "spend", label: t("analytics.tables.spend"), render: (row) => formatMoney(row.spend, currencyCode) },
    { key: "revenue", label: t("analytics.tables.revenue"), render: (row) => formatMoney(row.revenue, currencyCode) },
    ...(canSeeProfit ? [{key: "profit", label: t("analytics.tables.netProfit"), render: (row: NonNullable<typeof campaignPerformance.data>[number]) => row.net_profit == null ? UNAVAILABLE : formatMoney(row.net_profit, currencyCode)}] : []),
    { key: "orders", label: t("analytics.tables.orders"), render: (row) => row.orders },
    { key: "leads", label: t("analytics.tables.leads"), render: (row) => row.leads },
    { key: "roas", label: t("analytics.tables.roas"), render: (row) => row.roas ?? UNAVAILABLE },
  ]}
  empty={<EmptyState title={t("analytics.emptyStates.noAdvertising")} description={t("analytics.emptyStates.noAdvertisingDescription")} />}
  wide
/>
          <p className="mt-3 text-xs font-semibold text-text-muted">{t("analytics.advertising.trendNote", { days: advertisingTrend.data?.length ?? 0 })}</p>
        </ReportCard>

        <section className="grid gap-6 xl:grid-cols-2">
          <ReportCard title={t("analytics.customers.title")} subtitle={t("analytics.customers.subtitle")}><div className="mb-4 grid gap-3 md:grid-cols-2"><MetricCard label={t("analytics.metrics.newCustomers")} value={customersSummary.data?.new_customers ?? 0} /><MetricCard label={t("analytics.metrics.repeatCustomerRate")} value={formatPercentValue(customerSummary.repeatCustomerRate)} helper={t("analytics.tooltips.repeatCustomerRate")} /><MetricCard label={t("analytics.metrics.averageSpend") } value={customerSummary.averageSpend == null ? UNAVAILABLE : formatMoney(customerSummary.averageSpend, currencyCode)} /><MetricCard label={t("analytics.metrics.customersWithOrders")} value={customerSummary.customersWithOrders} /><MetricCard label={t("analytics.metrics.leadConversionRate")} value={formatPercentValue(leadConversionRate)} helper={t("analytics.tooltips.conversionRate")} /></div><ResponsiveReportTable
  rows={(customers.data ?? []).slice(0, 8)}
  rowKey={(row) => row.id}
  columns={[
    { key: "customer", label: t("analytics.tables.customer"), render: (row) => row.name ,emphasis: true },
    { key: "contact", label: t("analytics.tables.contact"), render: (row) => row.instagram_username ?? row.phone ?? UNAVAILABLE },
    { key: "orders", label: t("analytics.tables.orders"), render: (row) => row.total_orders },
    { key: "spent", label: t("analytics.tables.totalSpent"), render: (row) => formatMoney(row.total_spent, currencyCode) },
    { key: "last", label: t("analytics.tables.lastOrder"), render: (row) => row.last_order_at?.slice(0, 10) ?? UNAVAILABLE },
  ]}
  empty={<EmptyState title={t("analytics.emptyStates.noCustomers")} description={t("analytics.emptyStates.noCustomersDescription")} />}
  wide
/></ReportCard>
          <ReportCard title={t("analytics.inventory.title")} subtitle={t("analytics.inventory.subtitle")}><div className="mb-4 grid gap-3 md:grid-cols-2"><MetricCard label={t("analytics.metrics.lowStock")} value={inventoryReport.data?.low_stock_count ?? inventoryRollup.lowStockCount} helper={t("analytics.tooltips.lowStock")} /><MetricCard label={t("analytics.metrics.outOfStock")} value={inventoryReport.data?.out_of_stock_count ?? inventoryRollup.outOfStockCount} /><MetricCard label={t("analytics.metrics.reservedStock")} value={inventoryRollup.reservedQuantity} helper={t("analytics.tooltips.reservedStock")} /><MetricCard label={t("analytics.metrics.incomingStock")} value={inventoryRollup.incomingQuantity} /></div><ResponsiveReportTable
  rows={inventorySummary.data?.low_stock_items ?? []}
  rowKey={(row) => row.variant_id}
  columns={[
    { key: "product", label: t("analytics.tables.product"), render: (row) => row.product_name ,emphasis: true },
    { key: "sku", label: t("analytics.tables.sku"), render: (row) => row.variant_sku },
    { key: "stock", label: t("analytics.tables.stock"), render: (row) => row.stock_quantity },
    { key: "reserved", label: t("analytics.tables.reserved"), render: (row) => row.reserved_quantity },
    { key: "incoming", label: t("analytics.tables.incoming"), render: (row) => row.incoming_quantity },
    { key: "minimum", label: t("analytics.tables.minimum"), render: (row) => row.minimum_quantity },
    { key: "sales", label: t("analytics.tables.salesInPeriod"), render: (row) => productRows.find((product) => product.variant_id === row.variant_id)?.quantity_sold ?? 0 },
  ]}
  empty={<EmptyState title={t("analytics.emptyStates.noInventoryAlerts")} description={t("analytics.emptyStates.noInventoryAlertsDescription")} />}
  wide
/></ReportCard>
        </section>
    </WorkspacePage>
  );
}
