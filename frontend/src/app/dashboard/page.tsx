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
    violet: "from-violet-50 to-white text-violet-700",
    pink: "from-pink-50 to-white text-pink-700",
    orange: "from-orange-50 to-white text-orange-700",
    amber: "from-amber-50 to-white text-amber-700",
  };

  return (
    <div className={`rounded-[20px] border border-slate-100 bg-gradient-to-br ${tones[tone]} p-4 shadow-sm`}>
      <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-400">{label}</p>
      <p className="mt-2 text-2xl font-black text-slate-950">{value}</p>
    </div>
  );
}

export default function DashboardPage() {
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
      <div className="mx-auto grid max-w-7xl gap-6">
        <section className="rounded-[28px] bg-[linear-gradient(135deg,#6D28D9_0%,#EC4899_45%,#F97316_75%,#FACC15_100%)] p-5 text-white shadow-2xl shadow-pink-500/20 sm:p-6 lg:p-8">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-white/80 sm:text-sm">Sellora Dashboard</p>
          <h1 className="mt-3 text-3xl font-black leading-tight sm:text-5xl">CRM for Instagram stores</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-white/85 sm:text-base">
            Ліди, клієнти, замовлення, склад, відправлення, реклама, фінанси та аналітика — в одному сучасному SaaS-інтерфейсі.
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
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <LoadingSkeleton rows={2} title="Loading dashboard…" />
            <LoadingSkeleton rows={2} title="Loading orders…" />
            <LoadingSkeleton rows={2} title="Loading shipments…" />
            <LoadingSkeleton rows={2} title="Loading ads…" />
          </div>
        ) : null}

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <KpiCard label="Дохід" value={formatMoney(dashboard.data?.month_revenue, currencyCode)} trend="+12%" />
          <KpiCard label="Чистий прибуток" value={formatMoney(dashboard.data?.month_profit, currencyCode)} trend="+8%" />
          <KpiCard label="Замовлення" value={dashboard.data?.month_orders ?? 0} trend="+5%" />
          <KpiCard label="Нові ліди" value={advertising.data?.total_leads ?? 0} trend="+14%" />
          <KpiCard label="ROAS" value={advertising.data?.roas ?? "—"} trend="+3%" />
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.5fr_0.8fr]">
          <ChartCard title="Sales chart" subtitle="Revenue and profit trend">
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

          <ChartCard title="Order status" subtitle="Current funnel">
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
              <EmptyState title="No orders yet" description="Create your first order or import historical data to populate the order status funnel." />
            )}
          </ChartCard>
        </section>

        <section className="grid gap-6 xl:grid-cols-2">
          <ChartCard title="Logistics" subtitle="Shipment health for the current workspace">
            <div className="grid gap-3 sm:grid-cols-2">
              <MetricStrip label="In transit" value={shipments.data?.in_transit_count ?? 0} tone="violet" />
              <MetricStrip label="Arrived" value={shipments.data?.arrived_count ?? 0} tone="pink" />
              <MetricStrip label="Delivered today" value={shipments.data?.delivered_today ?? 0} tone="orange" />
              <MetricStrip label="Returned this month" value={shipments.data?.returned_this_month ?? 0} tone="amber" />
            </div>
          </ChartCard>

          <ChartCard title="Advertising" subtitle="Campaign signal overview">
            <div className="grid gap-3 sm:grid-cols-2">
              <MetricStrip label="Spend" value={formatMoney(advertising.data?.total_spend, currencyCode)} tone="violet" />
              <MetricStrip label="Messages" value={advertising.data?.total_messages ?? 0} tone="pink" />
              <MetricStrip label="Leads" value={advertising.data?.total_leads ?? 0} tone="orange" />
              <MetricStrip label="ROAS" value={advertising.data?.roas ?? "—"} tone="amber" />
            </div>
          </ChartCard>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
          <RecentOrdersTable orders={orders.data ?? []} currencyCode={currencyCode} />
          <TopProductsCard products={dashboard.data?.top_products ?? []} currencyCode={currencyCode} />
        </section>

        <section className="grid gap-6 lg:grid-cols-3">
          <NotificationsCard />
          <QuickActionsCard />
          <ActivityFeed />
        </section>
      </div>
    </main>
  );
}
