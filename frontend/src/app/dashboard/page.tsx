"use client";

import { useQuery } from "@tanstack/react-query";
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ActivityFeed } from "@/features/dashboard/components/activity-feed";
import { ChartCard } from "@/features/dashboard/components/chart-card";
import { KpiCard } from "@/features/dashboard/components/kpi-card";
import { NotificationsCard } from "@/features/dashboard/components/notifications-card";
import { QuickActionsCard } from "@/features/dashboard/components/quick-actions-card";
import { RecentOrdersTable } from "@/features/dashboard/components/recent-orders-table";
import { TopProductsCard } from "@/features/dashboard/components/top-products-card";
import { useAuth } from "@/hooks/use-auth";
import { fetchAnalyticsDashboard } from "@/services/analytics";
import { fetchAdvertisingSummary } from "@/services/advertising";
import { fetchOrders } from "@/services/orders";

const orderStatusData = [
  { name: "New", value: 32, color: "#7C3AED" },
  { name: "Shipped", value: 24, color: "#EC4899" },
  { name: "Delivered", value: 44, color: "#F97316" },
];

export default function DashboardPage() {
  const { currentWorkspaceId } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const enabled = Boolean(workspaceId);
  const dashboard = useQuery({ queryKey: ["dashboard", workspaceId], queryFn: () => fetchAnalyticsDashboard(workspaceId), enabled });
  const advertising = useQuery({ queryKey: ["dashboard-advertising", workspaceId], queryFn: () => fetchAdvertisingSummary(workspaceId), enabled });
  const orders = useQuery({ queryKey: ["dashboard-orders", workspaceId], queryFn: () => fetchOrders(workspaceId, ""), enabled });
  const trend = (dashboard.data?.sales_trend ?? []).map((item) => ({ ...item, revenueNumber: Number(item.revenue), profitNumber: Number(item.net_profit) }));

  return <main className="p-4 sm:p-6"><div className="mx-auto grid max-w-7xl gap-6"><section className="rounded-[28px] bg-[linear-gradient(135deg,#6D28D9_0%,#EC4899_45%,#F97316_75%,#FACC15_100%)] p-6 text-white shadow-2xl shadow-pink-500/20"><p className="text-sm font-bold uppercase tracking-[0.28em] text-white/80">Sellora Dashboard</p><h1 className="mt-3 text-3xl font-black sm:text-5xl">CRM for Instagram stores</h1><p className="mt-3 max-w-3xl text-white/85">Ліди, клієнти, замовлення, склад, відправлення, реклама, фінанси та аналітика — в одному сучасному SaaS-інтерфейсі.</p></section><section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5"><KpiCard label="Дохід" value={`$${dashboard.data?.month_revenue ?? "0.00"}`} trend="+12%" /><KpiCard label="Чистий прибуток" value={`$${dashboard.data?.month_profit ?? "0.00"}`} trend="+8%" /><KpiCard label="Замовлення" value={dashboard.data?.month_orders ?? 0} trend="+5%" /><KpiCard label="Нові ліди" value={advertising.data?.total_leads ?? 0} trend="+14%" /><KpiCard label="ROAS" value={advertising.data?.roas ?? "—"} trend="+3%" /></section><section className="grid gap-6 xl:grid-cols-[1.5fr_0.8fr]"><ChartCard title="Sales chart" subtitle="Revenue and profit trend"><div className="h-80"><ResponsiveContainer width="100%" height="100%"><AreaChart data={trend}><defs><linearGradient id="selloraRevenue" x1="0" x2="0" y1="0" y2="1"><stop offset="5%" stopColor="#7C3AED" stopOpacity={0.45}/><stop offset="95%" stopColor="#7C3AED" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="date" tick={{ fontSize: 12 }}/><YAxis tick={{ fontSize: 12 }}/><Tooltip/><Area type="monotone" dataKey="revenueNumber" stroke="#7C3AED" fill="url(#selloraRevenue)" strokeWidth={3}/><Area type="monotone" dataKey="profitNumber" stroke="#EC4899" fill="transparent" strokeWidth={3}/></AreaChart></ResponsiveContainer></div></ChartCard><ChartCard title="Order status" subtitle="Current funnel"><div className="h-80"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={orderStatusData} dataKey="value" nameKey="name" innerRadius={72} outerRadius={112} paddingAngle={4}>{orderStatusData.map((entry) => <Cell key={entry.name} fill={entry.color} />)}</Pie><Tooltip/></PieChart></ResponsiveContainer></div></ChartCard></section><section className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]"><RecentOrdersTable orders={orders.data ?? []} /><TopProductsCard products={dashboard.data?.top_products ?? []} /></section><section className="grid gap-6 lg:grid-cols-3"><NotificationsCard /><QuickActionsCard /><ActivityFeed /></section></div></main>;
}
