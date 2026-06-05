"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ActivityFeed } from "@/features/dashboard/components/activity-feed";
import { ChartCard } from "@/features/dashboard/components/chart-card";
import { KpiCard } from "@/features/dashboard/components/kpi-card";
import { NotificationsCard } from "@/features/dashboard/components/notifications-card";
import { QuickActionsCard } from "@/features/dashboard/components/quick-actions-card";
import { RecentOrdersTable } from "@/features/dashboard/components/recent-orders-table";
import { TopProductsCard } from "@/features/dashboard/components/top-products-card";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/states";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import { fetchAdvertisingSummary } from "@/services/advertising";
import { fetchAnalyticsDashboard } from "@/services/analytics";
import { fetchOrders } from "@/services/orders";
import { fetchShipmentSummary } from "@/services/shipments";
import { OrderStatus } from "@/types/orders";

const orderStatusColors: Record<OrderStatus, string> = {
  NEW: "#7C3AED",
  CONFIRMED: "#8B5CF6",
  SHIPPED: "#EC4899",
  DELIVERED: "#F97316",
  COMPLETED: "#16A34A",
  RETURNED: "#F59E0B",
  CANCELLED: "#94A3B8",
};

function MetricStrip({ label, value, tone = "violet" }: { label: string; value: string | number; tone?: "violet" | "pink" | "orange" | "amber" }) {
  const tones = {
    violet: "from-violet-50 to-white text-violet-700 dark:from-violet-500/20 dark:to-violet-400/10 dark:text-violet-100",
    pink: "from-pink-50 to-white text-pink-700 dark:from-pink-500/20 dark:to-pink-400/10 dark:text-pink-100",
    orange: "from-orange-50 to-white text-orange-700 dark:from-orange-500/20 dark:to-orange-400/10 dark:text-orange-100",
    amber: "from-amber-50 to-white text-amber-700 dark:from-amber-500/20 dark:to-amber-400/10 dark:text-amber-100",
  };

  return (
    <div className={`min-w-0 overflow-hidden rounded-[20px] border border-slate-100 bg-gradient-to-br ${tones[tone]} p-4 shadow-sm dark:border-white/10 dark:bg-slate-900/100 dark:shadow-none`}>
      <p className="break-words text-xs font-black uppercase tracking-[0.18em] text-slate-500 dark:text-slate-300">{label}</p>
      <p className="mt-2 truncate text-2xl font-black text-slate-950 dark:text-white">{value}</p>
    </div>
  );
}

export default function DashboardPage() {
  const { t, formatStatus } = useI18n();
  const { currentUser, currentWorkspace, currentWorkspaceId, status: authStatus } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const currencyCode = currentWorkspace?.currency_code ?? "UAH";
  const enabled = authStatus === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);

  const dashboard = useQuery({ queryKey: ["dashboard", workspaceId], queryFn: () => fetchAnalyticsDashboard(workspaceId), enabled });
  const advertising = useQuery({ queryKey: ["dashboard-advertising", workspaceId], queryFn: () => fetchAdvertisingSummary(workspaceId), enabled });
  const orders = useQuery({ queryKey: ["dashboard-orders", workspaceId], queryFn: () => fetchOrders(workspaceId, ""), enabled });
  const shipments = useQuery({ queryKey: ["dashboard-shipments", workspaceId], queryFn: () => fetchShipmentSummary(workspaceId), enabled });

  const trend = useMemo(
    () => (dashboard.data?.sales_trend ?? []).map((item) => ({ ...item, revenueNumber: Number(item.revenue), profitNumber: Number(item.net_profit) })),
    [dashboard.data?.sales_trend],
  );

  const orderStatusData = useMemo(() => {
    const counts = new Map<OrderStatus, number>();
    for (const order of orders.data ?? []) counts.set(order.status, (counts.get(order.status) ?? 0) + 1);
    return Array.from(counts.entries()).map(([name, value]) => ({ name, value, color: orderStatusColors[name] }));
  }, [orders.data]);

  const isLoading = dashboard.isLoading || advertising.isLoading || orders.isLoading || shipments.isLoading;
  const hasError = dashboard.isError || advertising.isError || orders.isError || shipments.isError;

  return (
    <main className="overflow-x-hidden p-4 sm:p-6">
      <div className="mx-auto grid min-w-0 max-w-7xl gap-6">
        <section className="rounded-[28px] bg-[linear-gradient(135deg,#6D28D9_0%,#EC4899_45%,#F97316_75%,#FACC15_100%)] p-5 text-white shadow-2xl shadow-pink-500/20 sm:p-6 lg:p-8">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-white/100 sm:text-sm">{t("dashboard.eyebrow")}</p>
          <h1 className="mt-3 text-3xl font-black leading-tight sm:text-5xl">{t("dashboard.title")}</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-white/105 sm:text-base">
            {t("dashboard.subtitle")}
          </p>
        </section>

        {hasError ? (
          <ErrorState
            description="Dashboard data could not be loaded. Refresh the page or retry after checking the current workspace connection."
            onRetry={() => {
              dashboard.refetch();
              advertising.refetch();
              orders.refetch();
              shipments.refetch();
            }}
          />
        ) : null}

        {isLoading ? (
          <div className="grid min-w-0 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <LoadingSkeleton rows={2} title="Loading dashboard…" />
            <LoadingSkeleton rows={2} title="Loading orders…" />
            <LoadingSkeleton rows={2} title="Loading shipments…" />
            <LoadingSkeleton rows={2} title="Loading ads…" />
          </div>
        ) : null}

        <section className="grid min-w-0 gap-4 md:grid-cols-2 xl:grid-cols-5">
          <KpiCard label="Дохід" value={formatMoney(dashboard.data?.month_revenue, currencyCode)} trend="+12%" />
          <KpiCard label="Чистий прибуток" value={formatMoney(dashboard.data?.month_profit, currencyCode)} trend="+8%" />
          <KpiCard label="Замовлення" value={dashboard.data?.month_orders ?? 0} trend="+5%" />
          <KpiCard label="Нові ліди" value={advertising.data?.total_leads ?? 0} trend="+14%" />
          <KpiCard label="ROAS" value={advertising.data?.roas ?? "—"} trend="+3%" />
        </section>

        <section className="grid min-w-0 gap-6 xl:grid-cols-[1.5fr_0.8fr]">
          <ChartCard title={t("dashboard.salesChart")} subtitle={t("analytics.subtitle")}>
            {trend.length ? (
              <div className="h-72 sm:h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trend} margin={{ left: -12, right: 8 }}>
                    <defs>
                      <linearGradient id="selloraRevenue" x1="0" x2="0" y1="0" y2="1">
                        <stop offset="5%" stopColor="#7C3AED" stopOpacity={0.45} />
                        <stop offset="95%" stopColor="#7C3AED" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Area type="monotone" dataKey="revenueNumber" stroke="#7C3AED" fill="url(#selloraRevenue)" strokeWidth={3} />
                    <Area type="monotone" dataKey="profitNumber" stroke="#EC4899" fill="transparent" strokeWidth={3} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <EmptyState title="No sales trend yet" description="Create orders or import historical data to see revenue and profit dynamics here." />
            )}
          </ChartCard>

          <ChartCard title={t("dashboard.orderStatus")} subtitle={t("dashboard.orderStatus")}>
            {orderStatusData.length ? (
              <div className="h-72 sm:h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={orderStatusData} dataKey="value" nameKey="name" innerRadius={72} outerRadius={112} paddingAngle={4}>
                      {orderStatusData.map((entry) => (
                        <Cell key={entry.name} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <EmptyState title={t("emptyStates.noOrders")} description={t("orders.subtitle")} />
            )}
          </ChartCard>
        </section>

        <section className="grid min-w-0 gap-6 xl:grid-cols-2">
          <ChartCard title={t("dashboard.logistics")} subtitle={t("shipments.subtitle")}>
            <div className="grid min-w-0 gap-3 sm:grid-cols-2">
              <MetricStrip label={t("dashboard.inTransit")} value={shipments.data?.in_transit_count ?? 0} tone="violet" />
              <MetricStrip label={t("dashboard.arrived")} value={shipments.data?.arrived_count ?? 0} tone="pink" />
              <MetricStrip label={t("dashboard.deliveredToday")} value={shipments.data?.delivered_today ?? 0} tone="orange" />
              <MetricStrip label={t("dashboard.returnedThisMonth")} value={shipments.data?.returned_this_month ?? 0} tone="amber" />
            </div>
          </ChartCard>

          <ChartCard title={t("dashboard.advertising")} subtitle={t("advertising.subtitle")}>
            <div className="grid min-w-0 gap-3 sm:grid-cols-2">
              <MetricStrip label={t("dashboard.spend")} value={formatMoney(advertising.data?.total_spend, currencyCode)} tone="violet" />
              <MetricStrip label={t("dashboard.messages")} value={advertising.data?.total_messages ?? 0} tone="pink" />
              <MetricStrip label={t("dashboard.leads")} value={advertising.data?.total_leads ?? 0} tone="orange" />
              <MetricStrip label="ROAS" value={advertising.data?.roas ?? "—"} tone="amber" />
            </div>
          </ChartCard>
        </section>

        <section className="grid min-w-0 gap-6 xl:grid-cols-[1.25fr_0.75fr]">
          <RecentOrdersTable orders={orders.data ?? []} currencyCode={currencyCode} />
          <TopProductsCard products={dashboard.data?.top_products ?? []} currencyCode={currencyCode} />
        </section>

        <section className="grid min-w-0 gap-6 lg:grid-cols-3">
          <NotificationsCard />
          <QuickActionsCard />
          <ActivityFeed />
        </section>
      </div>
    </main>
  );
}
