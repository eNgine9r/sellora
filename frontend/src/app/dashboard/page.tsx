"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ActivityFeed, DashboardActivity } from "@/features/dashboard/components/activity-feed";
import { ChartCard } from "@/features/dashboard/components/chart-card";
import { NotificationsCard, DashboardNotification } from "@/features/dashboard/components/notifications-card";
import { QuickActionsCard } from "@/features/dashboard/components/quick-actions-card";
import { RecentOrdersTable } from "@/features/dashboard/components/recent-orders-table";
import { TopProductsCard, TopProductView } from "@/features/dashboard/components/top-products-card";
import { DateRangeSelector } from "@/components/date-range-selector";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/states";
import { MetricCard, WorkspaceHeader, WorkspacePage } from "@/components/crm-workspace";
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
import { fetchShipmentSummary } from "@/services/shipments";
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


function OwnerActionCard({ title, description, href, action, tone = "violet" }: { title: string; description: string; href: string; action: string; tone?: "violet" | "amber" | "rose" | "emerald" }) {
  const tones = {
    violet: "border-violet-100 bg-violet-50 text-violet-800 dark:border-violet-400/20 dark:bg-violet-400/10 dark:text-violet-100",
    amber: "border-amber-100 bg-amber-50 text-amber-800 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-100",
    rose: "border-rose-100 bg-rose-50 text-rose-800 dark:border-rose-400/20 dark:bg-rose-400/10 dark:text-rose-100",
    emerald: "border-emerald-100 bg-emerald-50 text-emerald-800 dark:border-emerald-400/20 dark:bg-emerald-400/10 dark:text-emerald-100",
  };
  return <Link href={href} className={`grid min-w-0 gap-2 rounded-2xl border p-4 text-sm transition hover:-translate-y-0.5 hover:shadow-md ${tones[tone]}`}><strong className="break-words text-base">{title}</strong><span className="break-words font-semibold opacity-85">{description}</span><span className="mt-1 inline-flex min-h-10 items-center font-black underline underline-offset-4">{action}</span></Link>;
}

function OwnerMetricRow({ label, value, helper }: { label: string; value: string | number; helper?: string }) {
  return <div className="flex min-w-0 items-start justify-between gap-3 rounded-2xl bg-slate-50 px-3 py-2 text-sm dark:bg-white/5"><div className="min-w-0"><p className="break-words font-bold text-slate-800 dark:text-slate-100">{label}</p>{helper ? <p className="break-words text-xs font-semibold text-text-muted">{helper}</p> : null}</div><strong className="shrink-0 text-slate-950 dark:text-white">{value}</strong></div>;
}

function MetricStrip({ label, value, helper, tone = "violet" }: { label: string; value: string | number; helper?: string; tone?: "violet" | "pink" | "orange" | "amber" }) {
  const tones = {
    violet: "from-violet-50 to-white text-violet-700 dark:from-violet-500/20 dark:to-violet-400/10 dark:text-violet-100",
    pink: "from-pink-50 to-white text-pink-700 dark:from-pink-500/20 dark:to-pink-400/10 dark:text-pink-100",
    orange: "from-orange-50 to-white text-orange-700 dark:from-orange-500/20 dark:to-orange-400/10 dark:text-orange-100",
    amber: "from-amber-50 to-white text-amber-700 dark:from-amber-500/20 dark:to-amber-400/10 dark:text-amber-100",
  };
  return <div className={`min-w-0 overflow-hidden rounded-[20px] border border-slate-100 bg-gradient-to-br ${tones[tone]} p-4 shadow-sm dark:border-white/10 dark:bg-slate-900/100 dark:shadow-none`}><p className="break-words text-xs font-black uppercase tracking-[0.18em] text-slate-500 dark:text-slate-300">{label}</p><p className="mt-2 truncate text-2xl font-black text-slate-950 dark:text-white">{value}</p>{helper ? <p className="mt-1 text-xs font-semibold text-slate-500 dark:text-slate-300">{helper}</p> : null}</div>;
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
  const shipments = useQuery({ queryKey: ["dashboard-shipments", workspaceId], queryFn: () => fetchShipmentSummary(workspaceId), enabled });
  const products = useQuery({ queryKey: ["dashboard-products", workspaceId], queryFn: () => fetchProducts(workspaceId), enabled });
  const onboarding = useQuery({ queryKey: ["onboarding-status", workspaceId], queryFn: () => fetchOnboardingStatus(workspaceId), enabled });

  const currentOrders = useMemo(() => (orders.data ?? []).filter((order) => isInDateRange(order.created_at, range)), [orders.data, range]);
  const currentLeads = useMemo(() => (leads.data ?? []).filter((lead: Lead) => isInDateRange(lead.created_at, range)), [leads.data, range]);

  const trend = useMemo(() => (salesTrend.data ?? []).map((item) => ({ ...item, revenueNumber: toFiniteNumber(item.revenue), profitNumber: toFiniteNumber(item.net_profit), ordersCount: item.orders_count })), [salesTrend.data]);

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
    return { ...item, variant_id: item.variant_id ?? item.product_id, variant_sku: item.variant_sku ?? item.sku ?? "—", net_profit: item.net_profit ?? "0", categoryLabel: displayCategory(item.category ?? product?.category, t), imageUrl: item.image_url ?? productImage(product) };
  }), [backendDashboard.data?.products.top_products, productById, topProducts.data, t]);



  const dashboardNotifications: DashboardNotification[] = useMemo(() => [
    { label: t("dashboard.notificationsItems.lowStock"), value: backendDashboard.data?.inventory.low_stock_count ?? inventory.data?.low_stock_count ?? 0, href: "/inventory" },
    { label: t("dashboard.notificationsItems.outOfStock"), value: backendDashboard.data?.inventory.out_of_stock_count ?? inventory.data?.out_of_stock_count ?? 0, href: "/inventory" },
    { label: t("dashboard.notificationsItems.unpaidOrders"), value: currentOrders.filter((order) => order.payment_status !== "PAID").length, href: "/orders" },
    { label: t("dashboard.notificationsItems.returnedShipments"), value: shipments.data?.returned_this_month ?? 0, href: "/shipments" },
  ].filter((item) => item.value > 0), [backendDashboard.data?.inventory.low_stock_count, backendDashboard.data?.inventory.out_of_stock_count, currentOrders, inventory.data, shipments.data, t]);

  const dashboardActivity: DashboardActivity[] = useMemo(() => [
    ...currentOrders.slice(0, 3).map((order) => ({ label: t("dashboard.activityItems.orderCreated", { number: order.order_number }), date: order.created_at })),
    ...currentLeads.slice(0, 2).map((lead) => ({ label: t("dashboard.activityItems.leadCreated", { name: lead.name }), date: lead.created_at })),
  ].sort((left, right) => right.date.localeCompare(left.date)).slice(0, 5), [currentLeads, currentOrders, t]);

  const isLoading = backendDashboard.isLoading || salesSummary.isLoading || (canSeeProfit && salesTrend.isLoading) || advertising.isLoading || orders.isLoading || leads.isLoading || inventory.isLoading || shipments.isLoading;
  const hasError = backendDashboard.isError || salesSummary.isError || (canSeeProfit && salesTrend.isError) || advertising.isError || orders.isError || leads.isError || inventory.isError || shipments.isError;
  const currentOrderSummary = summarizeOrders(currentOrders);
  const previousOrderSummary = summarizeOrders(orders.data?.filter((order) => isInDateRange(order.created_at, previousRange)) ?? []);
  const totalRevenue = toFiniteNumber(backendDashboard.data?.sales.revenue ?? currentOrderSummary.revenue);
  const previousRevenue = toFiniteNumber(previousBackendDashboard.data?.sales.revenue ?? previousOrderSummary.revenue);
  const netProfit = canSeeProfit ? toFiniteNumber(backendDashboard.data?.sales.net_profit ?? profitSummary.data?.total_net_profit) : 0;
  const previousProfit = canSeeProfit ? toFiniteNumber(previousBackendDashboard.data?.sales.net_profit ?? previousProfitSummary.data?.total_net_profit) : 0;
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
  const profitMissing = canSeeProfit && totalRevenue > 0 && netProfit === 0;
  const selectedPeriodLabel = t(`dateRange.${range.preset}`);
  const ownerAlerts = [
    lowStockCount > 0 ? { title: t("dashboard.ownerAlerts.lowStock.title", { count: lowStockCount }), description: t("dashboard.ownerAlerts.lowStock.description"), href: "/inventory", action: t("dashboard.ownerActions.openInventory"), tone: "amber" as const } : null,
    confirmedOrders > 0 ? { title: t("dashboard.ownerAlerts.awaitingShipment.title", { count: confirmedOrders }), description: t("dashboard.ownerAlerts.awaitingShipment.description"), href: "/orders", action: t("dashboard.ownerActions.openOrders"), tone: "rose" as const } : null,
    profitMissing ? { title: t("dashboard.ownerAlerts.profitMissing.title"), description: t("dashboard.ownerAlerts.profitMissing.description"), href: "/products", action: t("dashboard.ownerActions.openProducts"), tone: "amber" as const } : null,
    !hasAdvertisingData ? { title: t("dashboard.ownerAlerts.noAds.title"), description: t("dashboard.ownerAlerts.noAds.description"), href: "/advertising", action: t("dashboard.ownerActions.openAdvertising"), tone: "violet" as const } : null,
    ordersCount === 0 && currentLeads.length === 0 ? { title: t("dashboard.ownerAlerts.noPeriodData.title"), description: t("dashboard.ownerAlerts.noPeriodData.description"), href: "/leads", action: t("dashboard.ownerActions.createLead"), tone: "emerald" as const } : null,
  ].filter(Boolean) as { title: string; description: string; href: string; action: string; tone: "violet" | "amber" | "rose" | "emerald" }[];
  const isFirstRun = !isLoading && !hasError && (onboarding.data?.progress_percent ?? 0) < 100;

  return (
    <WorkspacePage>
        <WorkspaceHeader title={t("dashboard.titleCompact")} description={t("dashboard.descriptionCompact")} actions={<DateRangeSelector compact />} />

        <DemoWorkspaceNotice workspace={currentWorkspace} />
        {isFirstRun ? <div className="grid gap-3"><FirstRunChecklist status={onboarding.data} />{currentWorkspace?.role === "OWNER" && !onboarding.data?.is_demo_workspace ? <div><DemoWorkspaceActions /></div> : null}</div> : null}
        {hasError ? <ErrorState description={t("dashboard.errors.loadFailed")} onRetry={() => { backendDashboard.refetch(); salesSummary.refetch(); if (canSeeProfit) { profitSummary.refetch(); salesTrend.refetch(); topProducts.refetch(); } advertising.refetch(); orders.refetch(); leads.refetch(); inventory.refetch(); shipments.refetch(); }} /> : null}
        {isLoading ? <div className="grid min-w-0 gap-4 md:grid-cols-2 xl:grid-cols-4"><LoadingSkeleton rows={2} title={t("dashboard.loading.dashboard")} /><LoadingSkeleton rows={2} title={t("dashboard.loading.orders")} /><LoadingSkeleton rows={2} title={t("dashboard.loading.shipments")} /><LoadingSkeleton rows={2} title={t("dashboard.loading.ads")} /></div> : null}
        <section data-dashboard-kpi-row className="grid min-w-0 gap-3 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard label={t("dashboard.kpis.orders")} value={ordersCount} helper={ordersCount ? t("dashboard.kpiHelpers.ordersHasData", { period: selectedPeriodLabel }) : t("dashboard.kpiHelpers.ordersZero")} trend={formatDeltaPercent(ordersCount, previousBackendDashboard.data?.sales.orders_count ?? previousOrderSummary.ordersCount)} tone="info" />
          <MetricCard label={t("dashboard.kpis.revenue")} value={formatMoney(totalRevenue, currencyCode)} helper={totalRevenue > 0 ? t("dashboard.kpiHelpers.revenueHasData", { period: selectedPeriodLabel }) : t("dashboard.kpiHelpers.revenueZero")} trend={formatDeltaPercent(totalRevenue, previousRevenue)} tone="success" />
          <MetricCard label={t("dashboard.kpis.netProfit")} value={canSeeProfit ? (profitMissing ? "—" : formatMoney(netProfit, currencyCode)) : t("dashboard.restricted")} helper={!canSeeProfit ? t("dashboard.kpiHelpers.profitRestricted") : profitMissing ? t("dashboard.kpiHelpers.profitMissing") : selectedPeriodLabel} trend={canSeeProfit && !profitMissing ? formatDeltaPercent(netProfit, previousProfit) : undefined} tone={profitMissing ? "warning" : "success"} isUnavailable={!canSeeProfit || profitMissing} />
          <MetricCard label={t("dashboard.kpis.roas")} value={hasAdvertisingData ? roas : "—"} helper={hasAdvertisingData ? t("dashboard.kpiHelpers.roasHasData") : t("dashboard.kpiHelpers.roasMissing")} trend={adSpend > 0 ? formatDeltaPercent(toFiniteNumber(backendDashboard.data?.advertising.roas ?? advertising.data?.roas), toFiniteNumber(previousBackendDashboard.data?.advertising.roas ?? previousAdvertising.data?.roas)) : undefined} tone={hasAdvertisingData ? "info" : "warning"} isUnavailable={!hasAdvertisingData} />
        </section>

        <section data-dashboard-operational-row className="grid min-w-0 gap-4 xl:grid-cols-12">
          <div className="min-w-0 xl:col-span-4">
            <ChartCard title={t("dashboard.ownerAlerts.title")} subtitle={t("dashboard.periodHelper", { period: selectedPeriodLabel })}>
              <div className="grid min-w-0 gap-2">
                {ownerAlerts.length ? ownerAlerts.slice(0, 4).map((alert) => <OwnerActionCard key={alert.title} {...alert} />) : <p className="rounded-2xl bg-success-surface px-4 py-3 text-sm font-bold text-success-foreground">{t("dashboard.ownerAlerts.allClear")}</p>}
              </div>
            </ChartCard>
          </div>
          <div className="min-w-0 xl:col-span-8">
            <ChartCard title={t("dashboard.funnel.title")} subtitle={t("dashboard.funnel.subtitle")}>
              {currentLeads.length || ordersCount ? <div className="grid min-w-0 gap-3 md:grid-cols-3"><MetricStrip label={t("dashboard.funnel.leads")} value={currentLeads.length} helper={t("dashboard.funnel.leadsHelp")} /><MetricStrip label={t("dashboard.funnel.orders")} value={ordersCount} helper={leadToOrderRate === null ? t("dashboard.funnel.noRate") : t("dashboard.funnel.orderRate", { rate: leadToOrderRate })} tone="pink" /><MetricStrip label={t("dashboard.funnel.delivered")} value={deliveredOrders} helper={deliveryRate === null ? t("dashboard.funnel.noRate") : t("dashboard.funnel.deliveryRate", { rate: deliveryRate })} tone="orange" /></div> : <EmptyState title={t("dashboard.funnel.emptyTitle")} description={t("dashboard.funnel.emptyDescription")} />}
            </ChartCard>
          </div>
        </section>

        <section data-dashboard-analytics-row className="grid min-w-0 gap-4 xl:grid-cols-12">
          <div className="min-w-0 xl:col-span-8">
            <ChartCard title={t("dashboard.charts.salesProfitTitle")} subtitle={t("dashboard.charts.salesProfitSubtitle")}>
              {trend.length ? <div className="h-60 sm:h-64"><ResponsiveContainer width="100%" height="100%"><AreaChart data={trend} margin={{ left: -12, right: 8 }}><defs><linearGradient id="selloraRevenue" x1="0" x2="0" y1="0" y2="1"><stop offset="5%" stopColor="#7C3AED" stopOpacity={0.45} /><stop offset="95%" stopColor="#7C3AED" stopOpacity={0} /></linearGradient></defs><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="date" tick={{ fontSize: 12 }} /><YAxis tick={{ fontSize: 12 }} /><Tooltip formatter={(value) => formatMoney(Number(value), currencyCode)} /><Area type="monotone" dataKey="revenueNumber" name={t("dashboard.kpis.revenue")} stroke="#7C3AED" fill="url(#selloraRevenue)" strokeWidth={3} /><Area type="monotone" dataKey="profitNumber" name={t("dashboard.kpis.netProfit")} stroke="#EC4899" fill="transparent" strokeWidth={3} /></AreaChart></ResponsiveContainer></div> : <EmptyState title={t("dashboard.emptyStates.noSalesTrend")} description={t("dashboard.emptyStates.noSalesTrendDescription")} />}
            </ChartCard>
          </div>
          <div className="min-w-0 xl:col-span-4">
            <ChartCard title={t("dashboard.charts.orderFunnelTitle")} subtitle={t("dashboard.charts.orderFunnelSubtitle")}>
              {orderStatusData.length ? <div className="grid gap-3"><div className="h-44"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={orderStatusData} dataKey="value" nameKey="label" innerRadius={42} outerRadius={70} paddingAngle={4}>{orderStatusData.map((entry) => <Cell key={entry.name} fill={entry.color} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer></div><div className="grid gap-2">{orderStatusData.map((status) => <div key={status.name} className="flex items-center justify-between gap-3 rounded-2xl bg-surface-2 px-3 py-2 text-sm"><span>{status.label}</span><strong>{status.value} · {status.percent}%</strong></div>)}</div></div> : <EmptyState title={t("dashboard.emptyStates.noOrdersInPeriod")} description={t("dashboard.emptyStates.noOrdersInPeriodDescription")} />}
            </ChartCard>
          </div>
        </section>

        <section data-dashboard-business-row className="grid min-w-0 gap-4 lg:grid-cols-2">
          <ChartCard title={t("dashboard.advertising.ownerTitle")} subtitle={t("dashboard.advertising.ownerSubtitle")}>{hasAdvertisingData ? <div className="grid min-w-0 gap-2 sm:grid-cols-2"><OwnerMetricRow label={t("dashboard.advertising.spend")} value={formatMoney(adSpend, currencyCode)} helper={t("dashboard.abbreviations.roas")} /><OwnerMetricRow label={t("dashboard.advertising.orders")} value={backendDashboard.data?.advertising.orders ?? advertising.data?.total_orders ?? 0} /><OwnerMetricRow label={t("dashboard.advertising.cpa")} value={backendDashboard.data?.advertising.cpa ? formatMoney(backendDashboard.data.advertising.cpa, currencyCode) : advertising.data?.average_cpa ? formatMoney(advertising.data.average_cpa, currencyCode) : "—"} helper={t("dashboard.abbreviations.cpa")} /><OwnerMetricRow label={t("dashboard.kpis.roas")} value={roas} /></div> : <EmptyState title={t("dashboard.advertising.emptyTitle")} description={t("dashboard.advertising.emptyDescription")} />}</ChartCard>
          <ChartCard title={t("dashboard.inventoryAlerts.ownerTitle")} subtitle={t("dashboard.inventoryAlerts.ownerSubtitle")}>{hasProductsData ? <div className="grid min-w-0 gap-2 sm:grid-cols-3"><OwnerMetricRow label={t("dashboard.inventoryAlerts.lowStock")} value={lowStockCount} helper={lowStockCount ? t("dashboard.inventoryAlerts.lowStockHelp", { count: lowStockCount }) : t("dashboard.inventoryAlerts.healthy")} /><OwnerMetricRow label={t("dashboard.inventoryAlerts.outOfStock")} value={outOfStockCount} /><OwnerMetricRow label={t("dashboard.inventoryAlerts.stockUnits")} value={inventory.data?.total_stock_units ?? 0} /></div> : <EmptyState title={t("dashboard.inventoryAlerts.emptyTitle")} description={t("dashboard.inventoryAlerts.emptyDescription")} />}</ChartCard>
        </section>

        <section data-dashboard-operational-lists className="grid min-w-0 gap-4 xl:grid-cols-12">
          <div className="min-w-0 xl:col-span-6"><RecentOrdersTable orders={(orders.data ?? []).slice(0, 8)} currencyCode={currencyCode} showProfit={canSeeProfit} /></div>
          <div className="min-w-0 xl:col-span-3"><NotificationsCard items={dashboardNotifications} /></div>
          <div className="min-w-0 xl:col-span-3"><ActivityFeed events={dashboardActivity} /></div>
        </section>

        <section className="grid min-w-0 gap-4 xl:grid-cols-[1fr_0.8fr]">
          <TopProductsCard products={topProductViews} currencyCode={currencyCode} showProfit={canSeeProfit} />
          <QuickActionsCard />
        </section>

      </WorkspacePage>
  );
}
