"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { ChevronDown } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { ActivityFeed, DashboardActivity } from "@/features/dashboard/components/activity-feed";
import { ChartCard } from "@/features/dashboard/components/chart-card";
import { DashboardMetricCard, DashboardActionList, DashboardFunnel } from "@/features/dashboard/components/dashboard-premium";
import { QuickActionsCard } from "@/features/dashboard/components/quick-actions-card";
import { RecentOrdersTable } from "@/features/dashboard/components/recent-orders-table";
import { TopProductsCard, TopProductView } from "@/features/dashboard/components/top-products-card";
import { DateRangeSelector } from "@/components/date-range-selector";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { WorkspaceHeader, WorkspacePage } from "@/components/crm-workspace";
import { DemoWorkspaceActions, DemoWorkspaceNotice, FirstRunChecklist } from "@/components/pilot-readiness";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { displayCategory } from "@/lib/categories";
import { ANALYTICS_ORDER_STATUSES, formatDeltaPercent, formatSafeRatio, isInDateRange, toFiniteNumber } from "@/lib/analytics-formulas";
import { formatMoney } from "@/lib/currency";
import { useDateRange } from "@/providers/date-range-provider";
import { fetchDashboardSummary } from "@/services/analytics";
import { fetchLeads } from "@/services/crm";
import { fetchOnboardingStatus } from "@/services/onboarding";
import { fetchOrders } from "@/services/orders";
import { fetchCodLedger } from "@/services/cod-reconciliation";
import { fetchExternalNovaPoshtaDocuments } from "@/services/shipments";
import type { ProductReportRow } from "@/types/analytics";
import { Lead } from "@/types/crm";
import { OrderStatus } from "@/types/orders";


type DashboardTopProductItem = ProductReportRow & { variant_id?: string; variant_sku?: string; net_profit?: string | null };

// Charting stays in separate chunks, and the secondary chart is mounted only
// when detailed analytics is expanded.
const SalesProfitChart = dynamic(
  () => import("@/features/dashboard/components/sales-profit-chart").then((module) => module.SalesProfitChart),
  { ssr: false, loading: () => <div aria-busy="true" className="h-52 animate-pulse rounded-lg bg-surface-2/70 motion-reduce:animate-none sm:h-60" /> },
);
const OrderStatusChart = dynamic(
  () => import("@/features/dashboard/components/order-status-chart").then((module) => module.OrderStatusChart),
  { ssr: false, loading: () => <div aria-busy="true" className="h-40 animate-pulse rounded-lg bg-surface-2/70 motion-reduce:animate-none" /> },
);

const orderStatusColors: Record<OrderStatus, string> = { NEW: "#7C3AED", CONFIRMED: "#8B5CF6", SHIPPED: "#EC4899", DELIVERED: "#F97316", COMPLETED: "#16A34A", RETURNED: "#F59E0B", CANCELLED: "#94A3B8" };

function OwnerMetricRow({ label, value, helper }: { label: string; value: string | number; helper?: string }) {
  return <div className="flex min-w-0 items-start justify-between gap-3 rounded-2xl bg-slate-50 px-3 py-2 text-sm dark:bg-white/5"><div className="min-w-0"><p className="break-words font-bold text-slate-800 dark:text-slate-100">{label}</p>{helper ? <p className="break-words text-xs font-semibold text-text-muted">{helper}</p> : null}</div><strong className="shrink-0 text-slate-950 dark:text-white">{value}</strong></div>;
}

export default function DashboardPage() {
  const { t, formatStatus } = useI18n();
  const [showDetails, setShowDetails] = useState(false);
  const { range, previousRange, isReady: periodReadyFromStorage } = useDateRange();
  const { currentUser, currentWorkspace, currentWorkspaceId, status: authStatus } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const currencyCode = currentWorkspace?.currency_code ?? "UAH";
  const enabled = periodReadyFromStorage && authStatus === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);
  const canSeeProfit = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "ANALYST";
  const canReviewExternalTtn = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";
  const dateFrom = range.date_from || undefined;
  const dateTo = range.date_to || undefined;
  const previousFrom = previousRange.date_from || undefined;
  const previousTo = previousRange.date_to || undefined;

  // One authoritative period report powers KPIs, chart, ads, stock and products.
  // Do not duplicate its aggregates with separate sales/profit/ads endpoints.
  const backendDashboard = useQuery({
    queryKey: ["dashboard-backend-summary", workspaceId, dateFrom, dateTo],
    queryFn: () => fetchDashboardSummary(workspaceId, undefined, dateFrom, dateTo),
    enabled, staleTime: 20_000, refetchInterval: 60_000,
    refetchOnWindowFocus: "always", refetchOnReconnect: "always", retry: 1,
  });
  const periodReady = backendDashboard.isSuccess;
  const previousBackendDashboard = useQuery({
    queryKey: ["dashboard-backend-summary-previous", workspaceId, previousFrom, previousTo],
    queryFn: () => fetchDashboardSummary(workspaceId, undefined, previousFrom, previousTo),
    enabled: enabled && periodReady && Boolean(previousFrom && previousTo),
    staleTime: 60_000,
  });
  const orders = useQuery({
    queryKey: ["orders", workspaceId, "", ""],
    queryFn: () => fetchOrders(workspaceId, ""),
    enabled: enabled && periodReady,
    staleTime: 20_000, refetchInterval: 60_000,
    refetchOnWindowFocus: "always", refetchOnReconnect: "always", retry: 1,
  });
  // Heavy activity/financial drill-down is fetched only when the user expands it.
  const leads = useQuery({
    queryKey: ["dashboard-leads", workspaceId],
    queryFn: () => fetchLeads(workspaceId, {}),
    enabled: enabled && periodReady && showDetails,
    staleTime: 60_000, refetchInterval: showDetails ? 90_000 : false,
    retry: 1,
  });
  const codLedger = useQuery({
    queryKey: ["cod-reconciliation", workspaceId, dateFrom, dateTo],
    queryFn: () => fetchCodLedger(dateFrom, dateTo),
    enabled: enabled && periodReady && showDetails,
    staleTime: 60_000, retry: 1,
  });
  const onboarding = useQuery({
    queryKey: ["onboarding-status", workspaceId],
    queryFn: () => fetchOnboardingStatus(workspaceId),
    enabled, staleTime: 5 * 60_000, retry: 1,
  });
  const externalTtns = useQuery({
    queryKey: ["np-external-inbox", workspaceId],
    queryFn: async () => {
      const [unmatched, conflicts] = await Promise.all([
        fetchExternalNovaPoshtaDocuments(workspaceId, "UNMATCHED"),
        fetchExternalNovaPoshtaDocuments(workspaceId, "CONFLICT"),
      ]);
      return [...conflicts, ...unmatched];
    },
    enabled: enabled && periodReady && canReviewExternalTtn,
    refetchInterval: 60_000,
    staleTime: 45_000,
  });

  const currentOrders = useMemo(() => (orders.data ?? []).filter((order) => isInDateRange(order.created_at, range)), [orders.data, range]);
  const currentLeads = useMemo(() => (leads.data ?? []).filter((lead: Lead) => isInDateRange(lead.created_at, range)), [leads.data, range]);

  const trend = useMemo(() => (backendDashboard.data?.sales.daily_rows ?? []).map((item) => ({ ...item, revenueNumber: toFiniteNumber(item.revenue), profitNumber: item.net_profit == null ? null : toFiniteNumber(item.net_profit), ordersCount: item.orders })), [backendDashboard.data?.sales.daily_rows]);

  const orderStatusData = useMemo(() => {
    const statusBreakdown = backendDashboard.data?.sales.order_status_breakdown;
    const total = backendDashboard.data?.sales.orders_count ?? currentOrders.length;
    return ANALYTICS_ORDER_STATUSES.map((status) => {
      const value = statusBreakdown ? Number(statusBreakdown[status] ?? 0) : currentOrders.filter((order) => order.status === status).length;
      return { name: status, label: formatStatus("order", status), value, percent: total ? Math.round((value / total) * 100) : 0, color: orderStatusColors[status] };
    }).filter((item) => item.value > 0);
  }, [backendDashboard.data?.sales.order_status_breakdown, backendDashboard.data?.sales.orders_count, currentOrders, formatStatus]);

  const topProductViews: TopProductView[] = useMemo(() => (backendDashboard.data?.products.top_products ?? []).map((item: DashboardTopProductItem) => ({
    ...item,
    variant_id: item.variant_id ?? item.product_id,
    variant_sku: item.variant_sku ?? item.sku ?? "—",
    net_profit: item.net_profit ?? null,
    categoryLabel: displayCategory(item.category, t),
    imageUrl: item.image_url ?? null,
  })), [backendDashboard.data?.products.top_products, t]);



  const dashboardActivity: DashboardActivity[] = useMemo(() => [
    ...currentOrders.slice(0, 3).map((order) => ({ label: t("dashboard.activityItems.orderCreated", { number: order.order_number }), date: order.created_at })),
    ...currentLeads.slice(0, 2).map((lead) => ({ label: t("dashboard.activityItems.leadCreated", { name: lead.name }), date: lead.created_at })),
  ].sort((left, right) => right.date.localeCompare(left.date)).slice(0, 5), [currentLeads, currentOrders, t]);

  // Pending or errored server metrics show "—", never a misleading zero.
  const totalRevenue = toFiniteNumber(backendDashboard.data?.sales.revenue);
  const previousRevenue = toFiniteNumber(previousBackendDashboard.data?.sales.revenue);
  const rawProfit = backendDashboard.data?.sales.net_profit;
  const rawPreviousProfit = previousBackendDashboard.data?.sales.net_profit;
  const netProfit = canSeeProfit ? toFiniteNumber(rawProfit) : 0;
  const previousProfit = canSeeProfit ? toFiniteNumber(rawPreviousProfit) : 0;
  const adSpend = toFiniteNumber(backendDashboard.data?.advertising.spend);
  const adRevenue = toFiniteNumber(backendDashboard.data?.advertising.revenue);
  const roas = adSpend > 0 ? formatSafeRatio(adRevenue, adSpend) : "—";
  const ordersCount = backendDashboard.data?.sales.orders_count ?? 0;
  const deliveredOrders = backendDashboard.data?.sales.delivered_orders ?? 0;
  const confirmedOrders = orderStatusData.find((item) => item.name === "CONFIRMED")?.value ?? 0;
  const leadToOrderRate = currentLeads.length ? Math.round((ordersCount / currentLeads.length) * 100) : null;
  const deliveryRate = ordersCount ? Math.round((deliveredOrders / ordersCount) * 100) : null;
  const lowStockCount = backendDashboard.data?.inventory.low_stock_count ?? 0;
  const outOfStockCount = backendDashboard.data?.inventory.out_of_stock_count ?? 0;
  const hasAdvertisingData = adSpend > 0 || adRevenue > 0 || (backendDashboard.data?.advertising.orders ?? 0) > 0;
  const hasProductsData = lowStockCount > 0 || outOfStockCount > 0 || (backendDashboard.data?.inventory.inventory_rows.length ?? 0) > 0 || (backendDashboard.data?.products.top_products.length ?? 0) > 0;
  const profitMissing = canSeeProfit && rawProfit == null;
  const selectedPeriodLabel = t(`dateRange.${range.preset}`);
  const ownerAlerts = [
    lowStockCount > 0 ? { title: t("dashboard.ownerAlerts.lowStock.title", { count: lowStockCount }), description: t("dashboard.ownerAlerts.lowStock.description"), href: "/inventory", action: t("dashboard.ownerActions.openInventory"), tone: "amber" as const } : null,
    confirmedOrders > 0 ? { title: t("dashboard.ownerAlerts.awaitingShipment.title", { count: confirmedOrders }), description: t("dashboard.ownerAlerts.awaitingShipment.description"), href: "/orders", action: t("dashboard.ownerActions.openOrders"), tone: "rose" as const } : null,
    profitMissing ? { title: t("dashboard.ownerAlerts.profitMissing.title"), description: t("dashboard.ownerAlerts.profitMissing.description"), href: "/orders", action: t("dashboard.ownerActions.openOrders"), tone: "amber" as const } : null,
    periodReady && !hasAdvertisingData ? { title: t("dashboard.ownerAlerts.noAds.title"), description: t("dashboard.ownerAlerts.noAds.description"), href: "/advertising", action: t("dashboard.ownerActions.openAdvertising"), tone: "violet" as const } : null,
    periodReady && leads.isSuccess && ordersCount === 0 && currentLeads.length === 0 ? { title: t("dashboard.ownerAlerts.noPeriodData.title"), description: t("dashboard.ownerAlerts.noPeriodData.description"), href: "/leads", action: t("dashboard.ownerActions.createLead"), tone: "emerald" as const } : null,
  ].filter(Boolean) as { title: string; description: string; href: string; action: string; tone: "violet" | "amber" | "rose" | "emerald" }[];
  const isFirstRun = onboarding.isSuccess && (onboarding.data?.progress_percent ?? 0) < 100;

  return (
    <WorkspacePage>
        <WorkspaceHeader title={t("dashboard.titleCompact")} description={t("dashboard.descriptionCompact")} actions={<DateRangeSelector compact />} />

        <DemoWorkspaceNotice workspace={currentWorkspace} />
        {isFirstRun ? <details className="group rounded-2xl border border-border-subtle bg-surface-1 px-4 py-3"><summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-semibold text-text-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"><span>{t("dashboard.onboarding.title")} · {onboarding.data?.progress_percent ?? 0}%</span><span className="text-xs text-primary group-open:hidden">{t("dashboard.onboarding.expand")}</span><span className="hidden text-xs text-primary group-open:inline">{t("dashboard.onboarding.collapse")}</span></summary><div className="mt-3 grid gap-3"><FirstRunChecklist status={onboarding.data} />{currentWorkspace?.role === "OWNER" && !onboarding.data?.is_demo_workspace ? <div><DemoWorkspaceActions /></div> : null}</div></details> : null}
        {backendDashboard.isError ? <ErrorState description={t("dashboard.errors.loadFailed")} onRetry={() => { void backendDashboard.refetch(); }} /> : null}
        {/* KPI labels and compact values are rendered immediately. Never block the
            whole dashboard on independent orders, leads or external provider calls. */}
        <section data-dashboard-kpi-row aria-label={t("dashboard.titleCompact")} className="grid min-w-0 grid-cols-2 gap-2.5 sm:gap-3 xl:grid-cols-4">
          <DashboardMetricCard label={t("dashboard.kpis.orders")} value={periodReady ? ordersCount : "—"} loading={!periodReady && !backendDashboard.isError} helper={periodReady && !ordersCount ? t("dashboard.kpiHelpers.ordersZero") : selectedPeriodLabel} trend={previousBackendDashboard.isSuccess ? formatDeltaPercent(ordersCount, previousBackendDashboard.data.sales.orders_count) : undefined} explanation={t("dashboard.tooltips.orders")} />
          <DashboardMetricCard label={t("dashboard.kpis.revenue")} value={periodReady ? formatMoney(totalRevenue, currencyCode) : "—"} loading={!periodReady && !backendDashboard.isError} helper={periodReady && totalRevenue === 0 ? ordersCount > 0 ? t("dashboard.kpiHelpers.revenueNoRecorded") : t("dashboard.kpiHelpers.revenueZero") : selectedPeriodLabel} trend={periodReady && previousBackendDashboard.isSuccess && totalRevenue > 0 ? formatDeltaPercent(totalRevenue, previousRevenue) : undefined} explanation={t("dashboard.tooltips.revenue")} />
          <DashboardMetricCard label={t("dashboard.kpis.netProfit")} value={!canSeeProfit ? t("dashboard.restricted") : periodReady && !profitMissing ? formatMoney(netProfit, currencyCode) : "—"} loading={!periodReady && !backendDashboard.isError && canSeeProfit} helper={!canSeeProfit ? t("dashboard.kpiHelpers.profitRestricted") : periodReady && profitMissing ? t("dashboard.kpiHelpers.profitMissing") : selectedPeriodLabel} trend={periodReady && canSeeProfit && !profitMissing && previousBackendDashboard.isSuccess && rawPreviousProfit != null && totalRevenue > 0 ? formatDeltaPercent(netProfit, previousProfit) : undefined} unavailable={!canSeeProfit || (periodReady && profitMissing)} emphasized explanation={t("dashboard.tooltips.netProfit")} />
          <DashboardMetricCard label={t("dashboard.kpis.roas")} value={periodReady && hasAdvertisingData ? roas : "—"} loading={!periodReady && !backendDashboard.isError} helper={periodReady && !hasAdvertisingData ? t("dashboard.kpiHelpers.roasMissing") : selectedPeriodLabel} trend={periodReady && previousBackendDashboard.isSuccess && adSpend > 0 ? formatDeltaPercent(toFiniteNumber(backendDashboard.data.advertising.roas), toFiniteNumber(previousBackendDashboard.data.advertising.roas)) : undefined} unavailable={periodReady && !hasAdvertisingData} explanation={t("dashboard.tooltips.roas")} />
        </section>

        {canReviewExternalTtn && (externalTtns.data?.length || externalTtns.isError) ? (
          <section data-dashboard-np-unmatched className="flex min-w-0 flex-wrap items-center justify-between gap-2 rounded-xl border border-border-subtle bg-surface-1 px-3 py-2">
            <div className="min-w-0">
              <p className="font-semibold text-text-primary">{t("shipments.externalReviewTitle")}: {externalTtns.data?.length ?? "—"}</p>
              <p className="hidden text-xs text-text-muted sm:block">{t("shipments.externalReviewDescription")}</p>
            </div>
            <Link href="/shipments" className="shrink-0 rounded-lg border border-border-subtle px-3 py-2 text-xs font-semibold text-primary transition hover:bg-surface-hover">
              {t("shipments.externalReviewAction")}
            </Link>
          </section>
        ) : null}

        <section data-dashboard-analytics-row className="grid min-w-0 items-start gap-3 xl:grid-cols-12">
          <div className="min-w-0 xl:col-span-8">
            <ChartCard title={t("dashboard.charts.salesProfitTitle")} subtitle={t("dashboard.charts.salesProfitSubtitle")}>
              {!canSeeProfit ? <EmptyState title={t("dashboard.restricted")} description={t("dashboard.kpiHelpers.profitRestricted")} /> : backendDashboard.isError ? <p role="status" className="rounded-lg bg-surface-2 p-3 text-xs text-text-secondary">{t("dashboard.errors.loadFailed")}</p> : !periodReady ? <div className="h-44 animate-pulse rounded-lg bg-surface-2/70 motion-reduce:animate-none" aria-busy="true" /> : trend.some((item) => item.revenueNumber !== 0 || item.profitNumber !== 0) ? <SalesProfitChart trend={trend} currencyCode={currencyCode} revenueLabel={t("dashboard.kpis.revenue")} profitLabel={t("dashboard.kpis.netProfit")} /> : <EmptyState title={t("dashboard.emptyStates.noSalesTrend")} description={ordersCount ? t("dashboard.emptyStates.noRecordedFinancials") : t("dashboard.emptyStates.noSalesTrendDescription")} />}
              {canSeeProfit ? <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-text-secondary"><span className="inline-flex items-center gap-2"><span aria-hidden="true" className="h-2 w-2 rounded-full bg-violet-500" />{t("dashboard.kpis.revenue")}</span>{canSeeProfit ? <span className="inline-flex items-center gap-2"><span aria-hidden="true" className="h-2 w-2 rounded-full bg-emerald-500" />{t("dashboard.kpis.netProfit")}</span> : null}</div> : null}
            </ChartCard>
          </div>
          <div className="min-w-0 xl:col-span-4">
            <ChartCard title={t("dashboard.ownerAlerts.title")} subtitle={t("dashboard.ownerAlerts.subtitleCompact")}>
              {periodReady ? <DashboardActionList items={ownerAlerts} emptyText={t("dashboard.ownerAlerts.allClear")} /> : backendDashboard.isError ? <p role="status" className="text-xs text-text-muted">{t("dashboard.errors.loadFailed")}</p> : <div className="grid gap-2" aria-busy="true"><div className="h-8 w-full animate-pulse rounded-lg bg-surface-2 motion-reduce:animate-none" /><div className="h-8 w-2/3 animate-pulse rounded-lg bg-surface-2 motion-reduce:animate-none" /></div>}
            </ChartCard>
          </div>
        </section>

        <section data-dashboard-operational-lists className="grid min-w-0 gap-4 xl:grid-cols-12">
          <div className="min-w-0 xl:col-span-8"><RecentOrdersTable orders={orders.data ?? []} currencyCode={currencyCode} showProfit={canSeeProfit} isLoading={orders.isPending && !backendDashboard.isError} isError={orders.isError || backendDashboard.isError} onRetry={() => { if (backendDashboard.isError) void backendDashboard.refetch(); else void orders.refetch(); }} /></div>
          <div className="min-w-0 xl:col-span-4"><QuickActionsCard /></div>
        </section>
        <details data-dashboard-secondary className="group min-w-0 overflow-hidden rounded-xl border border-border-subtle bg-surface-1" onToggle={(event) => setShowDetails(event.currentTarget.open)}>
          <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-semibold text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring [&::-webkit-details-marker]:hidden">
            <span>{t("dashboard.details.title")} <span className="ml-2 text-xs font-normal text-text-muted">{t("dashboard.details.subtitle")}</span></span>
            <ChevronDown aria-hidden="true" className="h-4 w-4 shrink-0 text-text-secondary transition-transform group-open:rotate-180" />
          </summary>
          {showDetails ? <div className="grid gap-3 border-t border-border-subtle p-3 sm:p-4">
        <section data-dashboard-operational-row className="grid min-w-0 items-start gap-3 xl:grid-cols-12">
          <div className="min-w-0 xl:col-span-8">
            <ChartCard title={t("dashboard.funnel.title")} subtitle={t("dashboard.funnel.subtitleAccurate")}>
              {leads.isPending ? <div className="h-24 animate-pulse rounded-lg bg-surface-2/70 motion-reduce:animate-none" aria-busy="true" /> : leads.isError ? <p role="status" className="text-xs text-text-muted">{t("dashboard.errors.loadFailed")}</p> : currentLeads.length || ordersCount ? <DashboardFunnel stages={[
                { label: t("dashboard.funnel.leads"), value: currentLeads.length, helper: t("dashboard.funnel.leadsHelp"), color: "bg-violet-500" },
                { label: t("dashboard.funnel.orders"), value: ordersCount, helper: leadToOrderRate === null ? t("dashboard.funnel.noRate") : t("dashboard.funnel.orderRatio", { rate: leadToOrderRate }), color: "bg-fuchsia-500" },
                { label: t("dashboard.funnel.delivered"), value: deliveredOrders, helper: deliveryRate === null ? t("dashboard.funnel.noRate") : t("dashboard.funnel.deliveryRate", { rate: deliveryRate }), color: "bg-emerald-500" },
              ]} /> : <EmptyState title={t("dashboard.funnel.emptyTitle")} description={t("dashboard.funnel.emptyDescription")} />}
            </ChartCard>
          </div>
          <div className="min-w-0 xl:col-span-4">
            <ChartCard title={t("dashboard.charts.orderFunnelTitle")} subtitle={t("dashboard.charts.orderFunnelSubtitle")}>
              {orderStatusData.length ? <OrderStatusChart statuses={orderStatusData} /> : <EmptyState title={t("dashboard.emptyStates.noOrdersInPeriod")} description={t("dashboard.emptyStates.noOrdersInPeriodDescription")} />}
            </ChartCard>
          </div>
        </section>
        <section data-dashboard-business-row className="grid min-w-0 gap-4 lg:grid-cols-2">
          <ChartCard title={t("dashboard.advertising.ownerTitle")} subtitle={t("dashboard.advertising.ownerSubtitle")}>{hasAdvertisingData ? <div className="grid min-w-0 gap-2 sm:grid-cols-2"><OwnerMetricRow label={t("dashboard.advertising.spend")} value={formatMoney(adSpend, currencyCode)} helper={t("dashboard.abbreviations.roas")} /><OwnerMetricRow label={t("dashboard.advertising.orders")} value={backendDashboard.data?.advertising.orders ?? 0} /><OwnerMetricRow label={t("dashboard.advertising.cpa")} value={backendDashboard.data?.advertising.cpa != null ? formatMoney(backendDashboard.data.advertising.cpa, currencyCode) : "—"} helper={t("dashboard.abbreviations.cpa")} /><OwnerMetricRow label={t("dashboard.kpis.roas")} value={roas} /></div> : <EmptyState title={t("dashboard.advertising.emptyTitle")} description={t("dashboard.advertising.emptyDescription")} />}</ChartCard>
          <ChartCard title={t("dashboard.inventoryAlerts.ownerTitle")} subtitle={t("dashboard.inventoryAlerts.ownerSubtitle")}>{hasProductsData ? <div className="grid min-w-0 gap-2 sm:grid-cols-2"><OwnerMetricRow label={t("dashboard.inventoryAlerts.lowStock")} value={lowStockCount} helper={lowStockCount ? t("dashboard.inventoryAlerts.lowStockHelp", { count: lowStockCount }) : t("dashboard.inventoryAlerts.healthy")} /><OwnerMetricRow label={t("dashboard.inventoryAlerts.outOfStock")} value={outOfStockCount} /></div> : <EmptyState title={t("dashboard.inventoryAlerts.emptyTitle")} description={t("dashboard.inventoryAlerts.emptyDescription")} />}</ChartCard>
        </section>
        <section className="grid min-w-0 gap-4 xl:grid-cols-[1fr_0.8fr]">
          <TopProductsCard products={topProductViews} currencyCode={currencyCode} showProfit={canSeeProfit} />
          {orders.isSuccess && leads.isSuccess ? <ActivityFeed events={dashboardActivity} /> : <div className="min-h-20 rounded-xl border border-border-subtle bg-surface-1 p-3 text-xs text-text-muted">{leads.isError ? t("dashboard.errors.loadFailed") : t("dashboard.activity")}</div>}
        </section>
        {codLedger.isError ? <p role="status" className="rounded-lg border border-border-subtle bg-surface-2 p-3 text-xs text-text-muted">{t("dashboard.errors.loadFailed")}</p> : null}
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
          </div> : null}
        </details>
      </WorkspacePage>
  );
}
