"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ActivityFeed, DashboardActivity } from "@/features/dashboard/components/activity-feed";
import { ChartCard } from "@/features/dashboard/components/chart-card";
import { KpiCard } from "@/features/dashboard/components/kpi-card";
import { NotificationsCard, DashboardNotification } from "@/features/dashboard/components/notifications-card";
import { QuickActionsCard } from "@/features/dashboard/components/quick-actions-card";
import { RecentOrdersTable } from "@/features/dashboard/components/recent-orders-table";
import { TopProductsCard, TopProductView } from "@/features/dashboard/components/top-products-card";
import { DateRangeSelector } from "@/components/date-range-selector";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/states";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { displayCategory } from "@/lib/categories";
import { ANALYTICS_ORDER_STATUSES, ANALYTICS_REVENUE_INCLUDED_STATUSES, formatDeltaPercent, formatSafeRatio, isInDateRange, summarizeOrders, toFiniteNumber } from "@/lib/analytics-formulas";
import { formatMoney } from "@/lib/currency";
import { useDateRange } from "@/providers/date-range-provider";
import { fetchAdvertisingSummary } from "@/services/advertising";
import { fetchDashboardSummary, fetchInventorySummary, fetchProfitSummary, fetchSalesSummary, fetchSalesTrend, fetchTopProducts } from "@/services/analytics";
import { fetchLeads } from "@/services/crm";
import { fetchOrders } from "@/services/orders";
import { fetchProducts, fetchProductVariants } from "@/services/products";
import { fetchShipmentSummary } from "@/services/shipments";
import { TopProduct } from "@/types/analytics";
import { Lead } from "@/types/crm";
import { Order, OrderStatus } from "@/types/orders";

const orderStatusColors: Record<OrderStatus, string> = { NEW: "#7C3AED", CONFIRMED: "#8B5CF6", SHIPPED: "#EC4899", DELIVERED: "#F97316", COMPLETED: "#16A34A", RETURNED: "#F59E0B", CANCELLED: "#94A3B8" };

function productImage(product?: { images?: { image_url: string; is_primary: boolean }[] }) {
  return product?.images?.find((image) => image.is_primary)?.image_url ?? product?.images?.[0]?.image_url ?? null;
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
  const previousSalesSummary = useQuery({ queryKey: ["dashboard-sales-summary-previous", workspaceId, previousFrom, previousTo], queryFn: () => fetchSalesSummary(workspaceId, undefined, previousFrom, previousTo), enabled: enabled && Boolean(previousFrom && previousTo) });
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
  const variants = useQuery({ queryKey: ["dashboard-variants", workspaceId], queryFn: () => fetchProductVariants(workspaceId, undefined, undefined), enabled });

  const currentOrders = useMemo(() => (orders.data ?? []).filter((order) => isInDateRange(order.created_at, range)), [orders.data, range.date_from, range.date_to]);
  const currentLeads = useMemo(() => (leads.data ?? []).filter((lead: Lead) => isInDateRange(lead.created_at, range)), [leads.data, range.date_from, range.date_to]);
  const previousLeads = useMemo(() => (leads.data ?? []).filter((lead: Lead) => isInDateRange(lead.created_at, previousRange)), [leads.data, previousRange.date_from, previousRange.date_to]);

  const trend = useMemo(() => (salesTrend.data ?? []).map((item) => ({ ...item, revenueNumber: toFiniteNumber(item.revenue), profitNumber: toFiniteNumber(item.net_profit), ordersCount: item.orders_count })), [salesTrend.data]);

  const orderStatusData = useMemo(() => {
    const total = currentOrders.length;
    return ANALYTICS_ORDER_STATUSES.map((status) => {
      const value = currentOrders.filter((order) => order.status === status).length;
      return { name: status, label: formatStatus("order", status), value, percent: total ? Math.round((value / total) * 100) : 0, color: orderStatusColors[status] };
    }).filter((item) => item.value > 0);
  }, [currentOrders, formatStatus]);

  const variantById = useMemo(() => new Map((variants.data ?? []).map((variant) => [variant.id, variant])), [variants.data]);
  const productById = useMemo(() => new Map((products.data ?? []).map((product) => [product.id, product])), [products.data]);

  const topProductViews: TopProductView[] = useMemo(() => (backendDashboard.data?.products.top_products ?? topProducts.data ?? []).map((item: TopProduct | any) => {
    const product = productById.get(item.product_id);
    return { ...item, variant_id: item.variant_id ?? item.product_id, variant_sku: item.variant_sku ?? item.sku ?? "—", net_profit: item.net_profit ?? "0", categoryLabel: displayCategory(item.category ?? product?.category, t), imageUrl: item.image_url ?? productImage(product) };
  }), [backendDashboard.data?.products.top_products, productById, topProducts.data, t]);

  const topCategories = useMemo(() => {
    const grouped = new Map<string, { categoryLabel: string; quantity: number; revenue: number; profit: number }>();
    currentOrders.filter((order) => ANALYTICS_REVENUE_INCLUDED_STATUSES.includes(order.status)).flatMap((order) => order.items).forEach((item) => {
      const variant = variantById.get(item.product_variant_id);
      const product = variant ? productById.get(variant.product_id) : undefined;
      const categoryLabel = displayCategory(product?.category, t);
      const current = grouped.get(categoryLabel) ?? { categoryLabel, quantity: 0, revenue: 0, profit: 0 };
      current.quantity += item.quantity;
      current.revenue += toFiniteNumber(item.line_total);
      current.profit += toFiniteNumber(item.line_total) - toFiniteNumber(item.line_cost);
      grouped.set(categoryLabel, current);
    });
    const totalRevenue = Array.from(grouped.values()).reduce((sum, item) => sum + item.revenue, 0);
    return Array.from(grouped.values()).sort((left, right) => right.revenue - left.revenue).slice(0, 6).map((item) => ({ ...item, share: totalRevenue ? Math.round((item.revenue / totalRevenue) * 100) : 0 }));
  }, [currentOrders, productById, t, variantById]);

  const dashboardNotifications: DashboardNotification[] = useMemo(() => [
    { label: t("dashboard.notificationsItems.lowStock"), value: backendDashboard.data?.inventory.low_stock_count ?? inventory.data?.low_stock_count ?? 0, href: "/inventory" },
    { label: t("dashboard.notificationsItems.outOfStock"), value: backendDashboard.data?.inventory.out_of_stock_count ?? inventory.data?.out_of_stock_count ?? 0, href: "/inventory" },
    { label: t("dashboard.notificationsItems.unpaidOrders"), value: currentOrders.filter((order) => order.payment_status !== "PAID").length, href: "/orders" },
    { label: t("dashboard.notificationsItems.returnedShipments"), value: shipments.data?.returned_this_month ?? 0, href: "/shipments" },
  ].filter((item) => item.value > 0), [currentOrders, inventory.data, shipments.data, t]);

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
  const roas = formatSafeRatio(adRevenue, adSpend);

  return (
    <main className="overflow-x-hidden p-4 sm:p-6">
      <div className="mx-auto grid min-w-0 max-w-7xl gap-6">
        <section className="rounded-[28px] bg-[linear-gradient(135deg,#6D28D9_0%,#EC4899_45%,#F97316_75%,#FACC15_100%)] p-5 text-white shadow-2xl shadow-pink-500/20 sm:p-6 lg:p-8">
          <div className="flex min-w-0 flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="min-w-0"><p className="text-xs font-bold uppercase tracking-[0.28em] text-white/100 sm:text-sm">{t("dashboard.eyebrow")}</p><h1 className="mt-3 text-3xl font-black leading-tight sm:text-5xl">{t("dashboard.title")}</h1><p className="mt-3 max-w-3xl text-sm leading-6 text-white/105 sm:text-base">{t("dashboard.subtitle")}</p></div>
            <div className="rounded-3xl bg-white/15 p-3 backdrop-blur"><DateRangeSelector compact /></div>
          </div>
        </section>

        {hasError ? <ErrorState description={t("dashboard.errors.loadFailed")} onRetry={() => { backendDashboard.refetch(); salesSummary.refetch(); if (canSeeProfit) { profitSummary.refetch(); salesTrend.refetch(); topProducts.refetch(); } advertising.refetch(); orders.refetch(); leads.refetch(); inventory.refetch(); shipments.refetch(); }} /> : null}
        {isLoading ? <div className="grid min-w-0 gap-4 md:grid-cols-2 xl:grid-cols-4"><LoadingSkeleton rows={2} title={t("dashboard.loading.dashboard")} /><LoadingSkeleton rows={2} title={t("dashboard.loading.orders")} /><LoadingSkeleton rows={2} title={t("dashboard.loading.shipments")} /><LoadingSkeleton rows={2} title={t("dashboard.loading.ads")} /></div> : null}

        <section className="grid min-w-0 gap-4 md:grid-cols-2 xl:grid-cols-5">
          <KpiCard label={t("dashboard.kpis.revenue")} value={formatMoney(totalRevenue, currencyCode)} helper={t("dashboard.tooltips.revenue")} trend={formatDeltaPercent(totalRevenue, previousRevenue)} />
          <KpiCard label={t("dashboard.kpis.netProfit")} value={canSeeProfit ? formatMoney(netProfit, currencyCode) : t("dashboard.restricted")} helper={t("dashboard.tooltips.netProfit")} trend={canSeeProfit ? formatDeltaPercent(netProfit, previousProfit) : undefined} />
          <KpiCard label={t("dashboard.kpis.orders")} value={backendDashboard.data?.sales.orders_count ?? currentOrderSummary.ordersCount} helper={t("dashboard.tooltips.orders")} trend={formatDeltaPercent(backendDashboard.data?.sales.orders_count ?? currentOrderSummary.ordersCount, previousBackendDashboard.data?.sales.orders_count ?? previousOrderSummary.ordersCount)} />
          <KpiCard label={t("dashboard.kpis.newLeads")} value={currentLeads.length} helper={t("dashboard.tooltips.newLeads")} trend={formatDeltaPercent(currentLeads.length, previousLeads.length)} />
          <KpiCard label={t("dashboard.kpis.roas")} value={roas} helper={t("dashboard.tooltips.roas")} trend={formatDeltaPercent(toFiniteNumber(backendDashboard.data?.advertising.roas ?? advertising.data?.roas), toFiniteNumber(previousBackendDashboard.data?.advertising.roas ?? previousAdvertising.data?.roas))} />
        </section>

        <section className="grid min-w-0 gap-6 xl:grid-cols-[1.45fr_0.85fr]">
          <ChartCard title={t("dashboard.charts.salesProfitTitle")} subtitle={t("dashboard.charts.salesProfitSubtitle")}>
            {trend.length ? <div className="h-72 sm:h-80"><ResponsiveContainer width="100%" height="100%"><AreaChart data={trend} margin={{ left: -12, right: 8 }}><defs><linearGradient id="selloraRevenue" x1="0" x2="0" y1="0" y2="1"><stop offset="5%" stopColor="#7C3AED" stopOpacity={0.45} /><stop offset="95%" stopColor="#7C3AED" stopOpacity={0} /></linearGradient></defs><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="date" tick={{ fontSize: 12 }} /><YAxis tick={{ fontSize: 12 }} /><Tooltip formatter={(value) => formatMoney(Number(value), currencyCode)} /><Area type="monotone" dataKey="revenueNumber" name={t("dashboard.kpis.revenue")} stroke="#7C3AED" fill="url(#selloraRevenue)" strokeWidth={3} /><Area type="monotone" dataKey="profitNumber" name={t("dashboard.kpis.netProfit")} stroke="#EC4899" fill="transparent" strokeWidth={3} /></AreaChart></ResponsiveContainer></div> : <EmptyState title={t("dashboard.emptyStates.noSalesTrend")} description={t("dashboard.emptyStates.noSalesTrendDescription")} />}
          </ChartCard>
          <ChartCard title={t("dashboard.charts.orderFunnelTitle")} subtitle={t("dashboard.charts.orderFunnelSubtitle")}>
            {orderStatusData.length ? <div className="grid gap-4"><div className="h-56"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={orderStatusData} dataKey="value" nameKey="label" innerRadius={54} outerRadius={88} paddingAngle={4}>{orderStatusData.map((entry) => <Cell key={entry.name} fill={entry.color} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer></div><div className="grid gap-2">{orderStatusData.map((status) => <div key={status.name} className="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-3 py-2 text-sm dark:bg-white/5"><span>{status.label}</span><strong>{status.value} · {status.percent}%</strong></div>)}</div></div> : <EmptyState title={t("dashboard.emptyStates.noOrdersInPeriod")} description={t("dashboard.emptyStates.noOrdersInPeriodDescription")} />}
          </ChartCard>
        </section>

        <section className="grid min-w-0 gap-6 xl:grid-cols-2">
          <TopProductsCard products={topProductViews} currencyCode={currencyCode} showProfit={canSeeProfit} />
          <ChartCard title={t("dashboard.topCategories.title")} subtitle={t("dashboard.topCategories.subtitle")}>
            {topCategories.length ? <div className="grid gap-3"><div className="h-56"><ResponsiveContainer width="100%" height="100%"><BarChart data={topCategories}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="categoryLabel" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} /><Tooltip formatter={(value) => formatMoney(Number(value), currencyCode)} /><Bar dataKey="revenue" name={t("dashboard.kpis.revenue")} fill="#7C3AED" radius={[8, 8, 0, 0]} /></BarChart></ResponsiveContainer></div>{topCategories.map((category) => <div key={category.categoryLabel} className="flex min-w-0 items-center justify-between gap-3 rounded-2xl bg-slate-50 px-3 py-2 text-sm dark:bg-white/5"><span className="truncate font-semibold">{category.categoryLabel} · {category.quantity} {t("dashboard.topCategories.sales")}</span><strong className="shrink-0">{formatMoney(category.revenue, currencyCode)} · {category.share}%</strong></div>)}</div> : <EmptyState title={t("dashboard.emptyStates.noCategories")} description={t("dashboard.emptyStates.noCategoriesDescription")} />}
          </ChartCard>
        </section>

        <section className="grid min-w-0 gap-6 xl:grid-cols-3">
          <ChartCard title={t("dashboard.advertising.title")} subtitle={t("dashboard.tooltips.roas")}><div className="grid min-w-0 gap-3 sm:grid-cols-2"><MetricStrip label={t("dashboard.advertising.spend")} value={formatMoney(adSpend, currencyCode)} /><MetricStrip label={t("dashboard.advertising.revenue")} value={formatMoney(adRevenue, currencyCode)} tone="pink" /><MetricStrip label={t("dashboard.advertising.messages")} value={backendDashboard.data?.advertising.messages ?? advertising.data?.total_messages ?? 0} tone="orange" /><MetricStrip label={t("dashboard.advertising.orders")} value={backendDashboard.data?.advertising.orders ?? advertising.data?.total_orders ?? 0} tone="amber" /><MetricStrip label={t("dashboard.advertising.cpa")} value={backendDashboard.data?.advertising.cpa ? formatMoney(backendDashboard.data.advertising.cpa, currencyCode) : advertising.data?.average_cpa ? formatMoney(advertising.data.average_cpa, currencyCode) : "—"} /><MetricStrip label={t("dashboard.advertising.cpl")} value={backendDashboard.data?.advertising.cpl ? formatMoney(backendDashboard.data.advertising.cpl, currencyCode) : advertising.data?.average_cpl ? formatMoney(advertising.data.average_cpl, currencyCode) : "—"} tone="pink" /></div></ChartCard>
          <ChartCard title={t("dashboard.inventoryAlerts.title")} subtitle={t("dashboard.inventoryAlerts.subtitle")}><div className="grid gap-3"><MetricStrip label={t("dashboard.inventoryAlerts.lowStock")} value={backendDashboard.data?.inventory.low_stock_count ?? inventory.data?.low_stock_count ?? 0} tone="amber" /><MetricStrip label={t("dashboard.inventoryAlerts.outOfStock")} value={backendDashboard.data?.inventory.out_of_stock_count ?? inventory.data?.out_of_stock_count ?? 0} tone="orange" /><MetricStrip label={t("dashboard.inventoryAlerts.stockUnits")} value={inventory.data?.total_stock_units ?? 0} tone="violet" />{inventory.data?.low_stock_items?.slice(0, 3).map((item) => <div key={item.variant_id} className="rounded-2xl bg-slate-50 p-3 text-sm dark:bg-white/5"><strong>{item.product_name}</strong><p className="text-slate-500 dark:text-slate-400">{item.variant_sku} · {item.stock_quantity}/{item.minimum_quantity}</p></div>)}{!inventory.data?.low_stock_count ? <p className="rounded-2xl bg-emerald-50 p-3 text-sm font-bold text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-100">{t("dashboard.inventoryAlerts.healthy")}</p> : null}</div></ChartCard>
          <ChartCard title={t("dashboard.logistics.title")} subtitle={t("dashboard.logistics.subtitle")}><div className="grid min-w-0 gap-3"><MetricStrip label={t("dashboard.logistics.inTransit")} value={shipments.data?.in_transit_count ?? 0} /><MetricStrip label={t("dashboard.logistics.arrived")} value={shipments.data?.arrived_count ?? 0} tone="pink" /><MetricStrip label={t("dashboard.logistics.deliveredToday")} value={shipments.data?.delivered_today ?? 0} tone="orange" /><MetricStrip label={t("dashboard.logistics.returnedThisMonth")} value={shipments.data?.returned_this_month ?? 0} tone="amber" /></div></ChartCard>
        </section>

        <section className="grid min-w-0 gap-6 xl:grid-cols-[1.25fr_0.75fr]"><RecentOrdersTable orders={currentOrders} currencyCode={currencyCode} showProfit={canSeeProfit} /><NotificationsCard items={dashboardNotifications} /></section>
        <section className="grid min-w-0 gap-6 lg:grid-cols-2"><ActivityFeed events={dashboardActivity} /><QuickActionsCard /></section>
      </div>
    </main>
  );
}
