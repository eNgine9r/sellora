"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ActivityFeed, DashboardActivity } from "@/features/dashboard/components/activity-feed";
import { ChartCard } from "@/features/dashboard/components/chart-card";
import { DashboardMetricCard, DashboardActionList, DashboardFunnel } from "@/features/dashboard/components/dashboard-premium";
import { QuickActionsCard } from "@/features/dashboard/components/quick-actions-card";
import { RecentOrdersTable } from "@/features/dashboard/components/recent-orders-table";
import { TopProductsCard, TopProductView } from "@/features/dashboard/components/top-products-card";
import { DateRangeSelector } from "@/components/date-range-selector";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/states";
import { WorkspaceHeader, WorkspacePage } from "@/components/crm-workspace";
import { DemoWorkspaceActions, DemoWorkspaceNotice, FirstRunChecklist } from "@/components/pilot-readiness";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { displayCategory } from "@/lib/categories";
import { ANALYTICS_ORDER_STATUSES, formatDeltaPercent, formatSafeRatio, isInDateRange, summarizeOrders, toFiniteNumber } from "@/lib/analytics-formulas";
import { formatMoney } from "@/lib/currency";
import { useDateRange } from "@/providers/date-range-provider";
import { fetchAdvertisingSummary } from "@/services/advertising";
import { fetchDashboardSummary, fetchInventorySummary, fetchProfitSummary, fetchSalesSummary, fetchSalesTrend, fetchTopProducts } from "@/services/analytics";
import { fetchLeads } from "@/services/crm";
import { fetchOnboardingStatus } from "@/services/onboarding";
import { fetchOrders } from "@/services/orders";
import { fetchProducts } from "@/services/products";
import { fetchCodLedger } from "@/services/cod-reconciliation";
import { TopProduct } from "@/types/analytics";
import { Lead } from "@/types/crm";
import { OrderStatus } from "@/types/orders";


type DashboardTopProductItem = TopProduct & {
  sku?: string | null;
  category?: string | null;
  image_url?: string | null;
};

const orderStatusColors: Record<OrderStatus, string> = { NEW: "#7C3AED", CONFIRMED: "#8B5CF6", SHIPPED: "#EC4899", DELIVERED: "#F97316", COMPLETED: "#16A34A", RETURNED: "#F59E0B", CANCELLED: "#94A3B8" };

function productImage(product?: { images?: { image_url: string; is_primary: boolean }[] }) {
  return product?.images?.find((image) => image.is_primary)?.image_url ?? product?.images?.[0]?.image_url ?? null;
}


function OwnerMetricRow({ label, value, helper }: { label: string; value: string | number; helper?: string }) {
  return <div className="flex min-w-0 items-start justify-between gap-3 rounded-2xl bg-slate-50 px-3 py-2 text-sm dark:bg-white/5"><div className="min-w-0"><p className="break-words font-bold text-slate-800 dark:text-slate-100">{label}</p>{helper ? <p className="break-words text-xs font-semibold text-text-muted">{helper}</p> : null}</div><strong className="shrink-0 text-slate-950 dark:text-white">{value}</strong></div>;
}

export default function DashboardPage() {
  const { t, formatStatus } = useI18n();
  const { range, previousRange } = useDateRange();
  const { currentUser, currentWorkspace, currentWorkspaceId, status: authStatus } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const currencyCode = currentWorkspace?.currency_code ?? "UAH";
  const enabled = authStatus === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);
  const canSeeProfit = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "ANALYST";
  const dateFrom = range.date_from || undefined;
  const dateTo = range.date_to || undefined;
  const previousFrom = previousRange.date_from || undefined;
  const previousTo = previousRange.date_to || undefined;

  const codLedger = useQuery({ queryKey: ["cod-reconciliation", workspaceId, dateFrom, dateTo], queryFn: () => fetchCodLedger(dateFrom, dateTo), enabled });
  const backendDashboard = useQuery({ queryKey: ["dashboard-backend-summary", workspaceId, dateFrom, dateTo], queryFn: () => fetchDashboardSummary(workspaceId, undefined, dateFrom, dateTo), enabled });
  const previousBackendDashboard = useQuery({ queryKey: ["dashboard-backend-summary-previous", workspaceId, previousFrom, previousTo], queryFn: () => fetchDashboardSummary(workspaceId, undefined, previousFrom, previousTo), enabled: enabled && Boolean(previousFrom && previousTo) });
  const salesSummary = useQuery({ queryKey: ["dashboard-sales-summary", workspaceId, dateFrom, dateTo], queryFn: () => fetchSalesSummary(workspaceId, undefined, dateFrom, dateTo), enabled });
  const profitSummary = useQuery({ queryKey: ["dashboard-profit-summary", workspaceId, dateFrom, dateTo], queryFn: () => fetchProfitSummary(workspaceId, undefined, dateFrom, dateTo), enabled: enabled && canSeeProfit });
  const previousProfitSummary = useQuery({ queryKey: ["dashboard-profit-summary-previous", workspaceId, previousFrom, previousTo], queryFn: () => fetchProfitSummary(workspaceId, undefined, previousFrom, previousTo), enabled: enabled && canSeeProfit && Boolean(previousFrom && previousTo) });
  const salesTrend = useQuery({ queryKey: ["dashboard-sales-trend", workspaceId, dateFrom, dateTo], queryFn: () => fetchSalesTrend(workspaceId, undefined, dateFrom, dateTo), enabled: enabled && canSeeProfit });
  const topProducts = useQuery({ queryKey: ["dashboard-top-products", workspaceId, dateFrom, dateTo], queryFn: () => fetchTopProducts(workspaceId, undefined, dateFrom, dateTo, 8), enabled: enabled && canSeeProfit });
  const advertising = useQuery({ queryKey: ["dashboard-advertising", workspaceId, dateFrom, dateTo], queryFn: () => fetchAdvertisingSummary(workspaceId, undefined, dateFrom, dateTo), enabled });
  const previousAdvertising = useQuery({ queryKey: ["dashboard-advertising-previous", workspaceId, previousFrom, previousTo], queryFn: () => fetchAdvertisingSummary(workspaceId, undefined, previousFrom, previousTo), enabled: enabled && Boolean(previousFrom && previousTo) });
  const orders = useQuery({ queryKey: ["dashboard-orders", workspaceId], queryFn: () => fetchOrders(workspaceId, ""), enabled });
  const leads = useQuery({ queryKey: ["dashboard-leads", workspaceId], queryFn: () => fetchLeads(workspaceId, {}), enabled });
  const inventory = useQuery({ queryKey: ["dashboard-inventory", workspaceId], queryFn: () => fetchInventorySummary(workspaceId), enabled });
  const products = useQuery({ queryKey: ["dashboard-products", workspaceId], queryFn: () => fetchProducts(workspaceId), enabled });
  const onboarding = useQuery({ queryKey: ["onboarding-status", workspaceId], queryFn: () => fetchOnboardingStatus(workspaceId), enabled });

  const currentOrders = useMemo(() => (orders.data ?? []).filter((order) => isInDateRange(order.created_at, range)), [orders.data, range]);
  const currentLeads = useMemo(() => (leads.data ?? []).filter((lead: Lead) => isInDateRange(lead.created_at, range)), [leads.data, range]);

  const trend = useMemo(() => (salesTrend.data ?? []).map((item) => ({ ...item, revenueNumber: toFiniteNumber(item.revenue), profitNumber: item.net_profit == null ? null : toFiniteNumber(item.net_profit), ordersCount: item.orders_count })), [salesTrend.data]);

  const orderStatusData = useMemo(() => {
    const total = currentOrders.length;
    return ANALYTICS_ORDER_STATUSES.map((status) => {
      const value = currentOrders.filter((order) => order.status === status).length;
      return { name: status, label: formatStatus("order", status), value, percent: total ? Math.round((value / total) * 100) : 0, color: orderStatusColors[status] };
    }).filter((item) => item.value > 0);
  }, [currentOrders, formatStatus]);

  const productById = useMemo(() => new Map((products.data ?? []).map((product) => [product.id, product])), [products.data]);

  const topProductViews: TopProductView[] = useMemo(() => ((backendDashboard.data?.products.top_products ?? topProducts.data ?? []) as DashboardTopProductItem[]).map((item) => {
    const product = productById.get(item.product_id);
    return { ...item, variant_id: item.variant_id ?? item.product_id, variant_sku: item.variant_sku ?? item.sku ?? "—", net_profit: item.net_profit ?? null, categoryLabel: displayCategory(item.category ?? product?.category, t), imageUrl: item.image_url ?? productImage(product) };
  }), [backendDashboard.data?.products.top_products, productById, topProducts.data, t]);



  const dashboardActivity: DashboardActivity[] = useMemo(() => [
    ...currentOrders.slice(0, 3).map((order) => ({ label: t("dashboard.activityItems.orderCreated", { number: order.order_number }), date: order.created_at })),
    ...currentLeads.slice(0, 2).map((lead) => ({ label: t("dashboard.activityItems.leadCreated", { name: lead.name }), date: lead.created_at })),
  ].sort((left, right) => right.date.localeCompare(left.date)).slice(0, 5), [currentLeads, currentOrders, t]);

  const isLoading = backendDashboard.isLoading || salesSummary.isLoading || (canSeeProfit && salesTrend.isLoading) || advertising.isLoading || orders.isLoading || leads.isLoading || inventory.isLoading;
  const hasError = backendDashboard.isError || salesSummary.isError || (canSeeProfit && salesTrend.isError) || advertising.isError || orders.isError || leads.isError || inventory.isError;
  const currentOrderSummary = summarizeOrders(currentOrders);
  const previousOrderSummary = summarizeOrders(orders.data?.filter((order) => isInDateRange(order.created_at, previousRange)) ?? []);
  const totalRevenue = toFiniteNumber(backendDashboard.data?.sales.revenue ?? currentOrderSummary.revenue);
  const previousRevenue = toFiniteNumber(previousBackendDashboard.data?.sales.revenue ?? previousOrderSummary.revenue);
  const rawProfit = backendDashboard.data ? backendDashboard.data.sales.net_profit : profitSummary.data?.total_net_profit;
  const rawPreviousProfit = previousBackendDashboard.data ? previousBackendDashboard.data.sales.net_profit : previousProfitSummary.data?.total_net_profit;
  const netProfit = canSeeProfit ? toFiniteNumber(rawProfit) : 0;
  const previousProfit = canSeeProfit ? toFiniteNumber(rawPreviousProfit) : 0;
  const adSpend = toFiniteNumber(backendDashboard.data?.advertising.spend ?? advertising.data?.total_spend);
  const adRevenue = toFiniteNumber(backendDashboard.data?.advertising.revenue ?? advertising.data?.total_revenue);
  const roas = adSpend > 0 ? formatSafeRatio(adRevenue, adSpend) : "—";
  const ordersCount = backendDashboard.data?.sales.orders_count ?? currentOrderSummary.ordersCount;
  const deliveredOrders = currentOrders.filter((order) => order.status === "DELIVERED" || order.status === "COMPLETED").length;
  const confirmedOrders = currentOrders.filter((order) => order.status === "CONFIRMED").length;
  const leadToOrderRate = currentLeads.length ? Math.round((ordersCount / currentLeads.length) * 100) : null;
  const deliveryRate = ordersCount ? Math.round((deliveredOrders / ordersCount) * 100) : null;
  const lowStockCount = backendDashboard.data?.inventory.low_stock_count ?? inventory.data?.low_stock_count ?? 0;
  const outOfStockCount = backendDashboard.data?.inventory.out_of_stock_count ?? inventory.data?.out_of_stock_count ?? 0;
  const hasAdvertisingData = adSpend > 0 || adRevenue > 0 || (backendDashboard.data?.advertising.orders ?? advertising.data?.total_orders ?? 0) > 0;
  const hasProductsData = (products.data?.length ?? 0) > 0 || (inventory.data?.total_stock_units ?? 0) > 0;
  const profitMissing = canSeeProfit && rawProfit == null;
  const selectedPeriodLabel = t(`dateRange.${range.preset}`);
  const ownerAlerts = [
    lowStockCount > 0 ? { title: t("dashboard.ownerAlerts.lowStock.title", { count: lowStockCount }), description: t("dashboard.ownerAlerts.lowStock.description"), href: "/inventory", action: t("dashboard.ownerActions.openInventory"), tone: "amber" as const } : null,
    confirmedOrders > 0 ? { title: t("dashboard.ownerAlerts.awaitingShipment.title", { count: confirmedOrders }), description: t("dashboard.ownerAlerts.awaitingShipment.description"), href: "/orders", action: t("dashboard.ownerActions.openOrders"), tone: "rose" as const } : null,
    profitMissing ? { title: t("dashboard.ownerAlerts.profitMissing.title"), description: t("dashboard.ownerAlerts.profitMissing.description"), href: "/orders", action: t("dashboard.ownerActions.openOrders"), tone: "amber" as const } : null,
    !hasAdvertisingData ? { title: t("dashboard.ownerAlerts.noAds.title"), description: t("dashboard.ownerAlerts.noAds.description"), href: "/advertising", action: t("dashboard.ownerActions.openAdvertising"), tone: "violet" as const } : null,
    ordersCount === 0 && currentLeads.length === 0 ? { title: t("dashboard.ownerAlerts.noPeriodData.title"), description: t("dashboard.ownerAlerts.noPeriodData.description"), href: "/leads", action: t("dashboard.ownerActions.createLead"), tone: "emerald" as const } : null,
  ].filter(Boolean) as { title: string; description: string; href: string; action: string; tone: "violet" | "amber" | "rose" | "emerald" }[];
  const isFirstRun = !isLoading && !hasError && onboarding.isSuccess && (onboarding.data?.progress_percent ?? 0) < 100;

  return (
    <WorkspacePage>
        <WorkspaceHeader title={t("dashboard.titleCompact")} description={t("dashboard.descriptionCompact")} actions={<DateRangeSelector compact />} />

        <DemoWorkspaceNotice workspace={currentWorkspace} />
        {isFirstRun ? <details className="group rounded-2xl border border-border-subtle bg-surface-1 px-4 py-3"><summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-semibold text-text-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"><span>{t("dashboard.onboarding.title")} · {onboarding.data?.progress_percent ?? 0}%</span><span className="text-xs text-primary group-open:hidden">{t("dashboard.onboarding.expand")}</span><span className="hidden text-xs text-primary group-open:inline">{t("dashboard.onboarding.collapse")}</span></summary><div className="mt-3 grid gap-3"><FirstRunChecklist status={onboarding.data} />{currentWorkspace?.role === "OWNER" && !onboarding.data?.is_demo_workspace ? <div><DemoWorkspaceActions /></div> : null}</div></details> : null}
        {hasError ? <ErrorState description={t("dashboard.errors.loadFailed")} onRetry={() => { backendDashboard.refetch(); salesSummary.refetch(); if (canSeeProfit) { profitSummary.refetch(); salesTrend.refetch(); topProducts.refetch(); } advertising.refetch(); orders.refetch(); leads.refetch(); inventory.refetch(); }} /> : null}
        {isLoading ? <div className="grid min-w-0 gap-4 md:grid-cols-2 xl:grid-cols-4"><LoadingSkeleton rows={2} title={t("dashboard.loading.dashboard")} /><LoadingSkeleton rows={2} title={t("dashboard.loading.orders")} /><LoadingSkeleton rows={2} title={t("dashboard.loading.shipments")} /><LoadingSkeleton rows={2} title={t("dashboard.loading.ads")} /></div> : null}
        {!isLoading && !hasError ? <>
        <section data-dashboard-kpi-row aria-label={t("dashboard.titleCompact")} className="grid min-w-0 grid-cols-2 gap-2.5 sm:gap-3 xl:grid-cols-4">
          <DashboardMetricCard label={t("dashboard.kpis.orders")} value={ordersCount} helper={ordersCount ? selectedPeriodLabel : t("dashboard.kpiHelpers.ordersZero")} trend={previousBackendDashboard.data || orders.data ? formatDeltaPercent(ordersCount, previousBackendDashboard.data?.sales.orders_count ?? previousOrderSummary.ordersCount) : undefined} explanation={t("dashboard.tooltips.orders")} />
          <DashboardMetricCard label={t("dashboard.kpis.revenue")} value={formatMoney(totalRevenue, currencyCode)} helper={totalRevenue > 0 ? selectedPeriodLabel : ordersCount > 0 ? t("dashboard.kpiHelpers.revenueNoRecorded") : t("dashboard.kpiHelpers.revenueZero")} trend={totalRevenue > 0 ? formatDeltaPercent(totalRevenue, previousRevenue) : undefined} explanation={t("dashboard.tooltips.revenue")} />
          <DashboardMetricCard label={t("dashboard.kpis.netProfit")} value={canSeeProfit ? (profitMissing ? "—" : formatMoney(netProfit, currencyCode)) : t("dashboard.restricted")} helper={!canSeeProfit ? t("dashboard.kpiHelpers.profitRestricted") : profitMissing ? t("dashboard.kpiHelpers.profitMissing") : selectedPeriodLabel} trend={canSeeProfit && !profitMissing && rawPreviousProfit != null && totalRevenue > 0 ? formatDeltaPercent(netProfit, previousProfit) : undefined} unavailable={!canSeeProfit || profitMissing} emphasized explanation={t("dashboard.tooltips.netProfit")} />
          <DashboardMetricCard label={t("dashboard.kpis.roas")} value={hasAdvertisingData ? roas : "—"} helper={hasAdvertisingData ? selectedPeriodLabel : t("dashboard.kpiHelpers.roasMissing")} trend={adSpend > 0 ? formatDeltaPercent(toFiniteNumber(backendDashboard.data?.advertising.roas ?? advertising.data?.roas), toFiniteNumber(previousBackendDashboard.data?.advertising.roas ?? previousAdvertising.data?.roas)) : undefined} unavailable={!hasAdvertisingData} explanation={t("dashboard.tooltips.roas")} />
        </section>

        {codLedger.data ? <section className="grid gap-2 sm:grid-cols-2" aria-label={t("dashboard.codReconciliation.title")} data-dashboard-cod-payments="true">
          <div className="min-w-0 rounded-xl border border-border-subtle bg-surface-1 p-3">
            <p className="text-xs font-medium text-text-secondary">{t("dashboard.codReconciliation.received")}</p>
            <p className="mt-1 text-lg font-bold">{formatMoney(codLedger.data.matched_receipts, currencyCode)}</p>
            <p className="text-xs text-text-muted">{selectedPeriodLabel} · {codLedger.data.matched_count}</p>
          </div>
          <div className="min-w-0 rounded-xl border border-border-subtle bg-surface-1 p-3">
            <p className="text-xs font-medium text-text-secondary">{t("dashboard.codReconciliation.pending")}</p>
            <p className="mt-1 text-lg font-bold">{formatMoney(codLedger.data.pending_historical_amount, currencyCode)}</p>
            <p className="text-xs text-text-muted">{t("dashboard.codReconciliation.unverified")} · {codLedger.data.historical_amount_unverified_count}</p>
          </div>
        </section> : null}
        <section data-dashboard-analytics-row className="grid min-w-0 items-start gap-3 xl:grid-cols-12">
          <div className="min-w-0 xl:col-span-8">
            <ChartCard title={t("dashboard.charts.salesProfitTitle")} subtitle={t("dashboard.charts.salesProfitSubtitle")}>
              {!canSeeProfit ? <EmptyState title={t("dashboard.restricted")} description={t("dashboard.kpiHelpers.profitRestricted")} /> : trend.some((item) => item.revenueNumber !== 0 || item.profitNumber !== 0) ? <div className="h-64 sm:h-72"><ResponsiveContainer width="100%" height="100%"><AreaChart data={trend} margin={{ top: 8, left: -12, right: 8, bottom: 2 }}><defs><linearGradient id="selloraRevenue" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="var(--primary-hover)" stopOpacity={0.3} /><stop offset="95%" stopColor="var(--primary-hover)" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--text-secondary)" }} tickLine={false} axisLine={false} minTickGap={28} /><YAxis tick={{ fontSize: 11, fill: "var(--text-secondary)" }} tickLine={false} axisLine={false} width={45} /><Tooltip contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border-default)", borderRadius: 12, color: "var(--text-primary)" }} formatter={(value) => formatMoney(Number(value), currencyCode)} /><Area type="monotone" dataKey="revenueNumber" name={t("dashboard.kpis.revenue")} stroke="var(--primary-hover)" fill="url(#selloraRevenue)" strokeWidth={2.5} activeDot={{ r: 5 }} /><Area type="monotone" dataKey="profitNumber" name={t("dashboard.kpis.netProfit")} stroke="var(--success)" fill="transparent" strokeWidth={2.5} activeDot={{ r: 5 }} /></AreaChart></ResponsiveContainer></div> : <EmptyState title={t("dashboard.emptyStates.noSalesTrend")} description={ordersCount ? t("dashboard.emptyStates.noRecordedFinancials") : t("dashboard.emptyStates.noSalesTrendDescription")} />}
              {canSeeProfit ? <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-text-secondary"><span className="inline-flex items-center gap-2"><span aria-hidden="true" className="h-2 w-2 rounded-full bg-violet-500" />{t("dashboard.kpis.revenue")}</span>{canSeeProfit ? <span className="inline-flex items-center gap-2"><span aria-hidden="true" className="h-2 w-2 rounded-full bg-emerald-500" />{t("dashboard.kpis.netProfit")}</span> : null}</div> : null}
            </ChartCard>
          </div>
          <div className="min-w-0 xl:col-span-4">
            <ChartCard title={t("dashboard.ownerAlerts.title")} subtitle={t("dashboard.ownerAlerts.subtitleCompact")}>
              <DashboardActionList items={ownerAlerts} emptyText={t("dashboard.ownerAlerts.allClear")} />
            </ChartCard>
          </div>
        </section>

        <section data-dashboard-operational-row className="grid min-w-0 items-start gap-3 xl:grid-cols-12">
          <div className="min-w-0 xl:col-span-8">
            <ChartCard title={t("dashboard.funnel.title")} subtitle={t("dashboard.funnel.subtitleAccurate")}>
              {currentLeads.length || ordersCount ? <DashboardFunnel stages={[
                { label: t("dashboard.funnel.leads"), value: currentLeads.length, helper: t("dashboard.funnel.leadsHelp"), color: "bg-violet-500" },
                { label: t("dashboard.funnel.orders"), value: ordersCount, helper: leadToOrderRate === null ? t("dashboard.funnel.noRate") : t("dashboard.funnel.orderRatio", { rate: leadToOrderRate }), color: "bg-fuchsia-500" },
                { label: t("dashboard.funnel.delivered"), value: deliveredOrders, helper: deliveryRate === null ? t("dashboard.funnel.noRate") : t("dashboard.funnel.deliveryRate", { rate: deliveryRate }), color: "bg-emerald-500" },
              ]} /> : <EmptyState title={t("dashboard.funnel.emptyTitle")} description={t("dashboard.funnel.emptyDescription")} />}
            </ChartCard>
          </div>
          <div className="min-w-0 xl:col-span-4">
            <ChartCard title={t("dashboard.charts.orderFunnelTitle")} subtitle={t("dashboard.charts.orderFunnelSubtitle")}>
              {orderStatusData.length ? <div className="grid gap-2"><div className="h-40"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={orderStatusData} dataKey="value" nameKey="label" innerRadius={48} outerRadius={69} paddingAngle={3}>{orderStatusData.map((entry) => <Cell key={entry.name} fill={entry.color} />)}</Pie><Tooltip contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border-default)", borderRadius: 12, color: "var(--text-primary)" }} /></PieChart></ResponsiveContainer></div><div className="grid gap-1">{orderStatusData.map((status) => <div key={status.name} className="flex items-center justify-between gap-3 rounded-lg px-2 py-1.5 text-xs text-text-secondary"><span className="flex items-center gap-2"><span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: status.color }} />{status.label}</span><strong className="font-semibold tabular-nums text-text-primary">{status.value} · {status.percent}%</strong></div>)}</div></div> : <EmptyState title={t("dashboard.emptyStates.noOrdersInPeriod")} description={t("dashboard.emptyStates.noOrdersInPeriodDescription")} />}
            </ChartCard>
          </div>
        </section>
        </> : null}

        {!isLoading && !hasError ? <>
        <section data-dashboard-business-row className="grid min-w-0 gap-4 lg:grid-cols-2">
          <ChartCard title={t("dashboard.advertising.ownerTitle")} subtitle={t("dashboard.advertising.ownerSubtitle")}>{hasAdvertisingData ? <div className="grid min-w-0 gap-2 sm:grid-cols-2"><OwnerMetricRow label={t("dashboard.advertising.spend")} value={formatMoney(adSpend, currencyCode)} helper={t("dashboard.abbreviations.roas")} /><OwnerMetricRow label={t("dashboard.advertising.orders")} value={backendDashboard.data?.advertising.orders ?? advertising.data?.total_orders ?? 0} /><OwnerMetricRow label={t("dashboard.advertising.cpa")} value={backendDashboard.data?.advertising.cpa ? formatMoney(backendDashboard.data.advertising.cpa, currencyCode) : advertising.data?.average_cpa ? formatMoney(advertising.data.average_cpa, currencyCode) : "—"} helper={t("dashboard.abbreviations.cpa")} /><OwnerMetricRow label={t("dashboard.kpis.roas")} value={roas} /></div> : <EmptyState title={t("dashboard.advertising.emptyTitle")} description={t("dashboard.advertising.emptyDescription")} />}</ChartCard>
          <ChartCard title={t("dashboard.inventoryAlerts.ownerTitle")} subtitle={t("dashboard.inventoryAlerts.ownerSubtitle")}>{hasProductsData ? <div className="grid min-w-0 gap-2 sm:grid-cols-3"><OwnerMetricRow label={t("dashboard.inventoryAlerts.lowStock")} value={lowStockCount} helper={lowStockCount ? t("dashboard.inventoryAlerts.lowStockHelp", { count: lowStockCount }) : t("dashboard.inventoryAlerts.healthy")} /><OwnerMetricRow label={t("dashboard.inventoryAlerts.outOfStock")} value={outOfStockCount} /><OwnerMetricRow label={t("dashboard.inventoryAlerts.stockUnits")} value={inventory.data?.total_stock_units ?? 0} /></div> : <EmptyState title={t("dashboard.inventoryAlerts.emptyTitle")} description={t("dashboard.inventoryAlerts.emptyDescription")} />}</ChartCard>
        </section>

        <section data-dashboard-operational-lists className="grid min-w-0 gap-4 xl:grid-cols-12">
          <div className="min-w-0 xl:col-span-8"><RecentOrdersTable orders={(orders.data ?? []).slice(0, 8)} currencyCode={currencyCode} showProfit={canSeeProfit} /></div>
          <div className="min-w-0 xl:col-span-4"><ActivityFeed events={dashboardActivity} /></div>
        </section>

        <section className="grid min-w-0 gap-4 xl:grid-cols-[1fr_0.8fr]">
          <TopProductsCard products={topProductViews} currencyCode={currencyCode} showProfit={canSeeProfit} />
          <QuickActionsCard />
        </section>
        </> : null}

      </WorkspacePage>
  );
}
