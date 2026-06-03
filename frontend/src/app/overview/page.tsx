"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { AnalyticsKpiCard } from "@/features/analytics/components/analytics-kpi-card";
import { RevenueTrendChart } from "@/features/analytics/components/revenue-trend-chart";
import { TopProductsTable } from "@/features/analytics/components/top-products-table";
import { fetchAnalyticsDashboard } from "@/services/analytics";
import { fetchAdvertisingSummary } from "@/services/advertising";
import { useAuth } from "@/hooks/use-auth";

export default function OverviewPage() {
  const { currentWorkspaceId } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const dashboard = useQuery({ queryKey: ["overview-dashboard", workspaceId], queryFn: () => fetchAnalyticsDashboard(workspaceId, undefined), enabled: Boolean(workspaceId) });
  const advertising = useQuery({ queryKey: ["overview-advertising", workspaceId], queryFn: () => fetchAdvertisingSummary(workspaceId, undefined), enabled: Boolean(workspaceId) });
  return <main className="min-h-screen bg-slate-100 p-6 text-slate-950"><div className="mx-auto grid max-w-7xl gap-6"><header className="rounded-2xl bg-white p-6 shadow-sm"><p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Sellora Overview</p><h1 className="mt-2 text-3xl font-bold">Business Dashboard</h1><p className="mt-1 text-slate-600">Daily and monthly order, revenue, profit, and inventory health.</p></header><section className="grid gap-4 md:grid-cols-4"><AnalyticsKpiCard label="Today Orders" value={dashboard.data?.today_orders ?? 0} /><AnalyticsKpiCard label="Today Revenue" value={dashboard.data?.today_revenue ?? "0.00"} /><AnalyticsKpiCard label="Today Profit" value={dashboard.data?.today_profit ?? "0.00"} /><AnalyticsKpiCard label="Low Stock" value={dashboard.data?.low_stock_count ?? 0} /><AnalyticsKpiCard label="Month Orders" value={dashboard.data?.month_orders ?? 0} /><AnalyticsKpiCard label="Month Revenue" value={dashboard.data?.month_revenue ?? "0.00"} /><AnalyticsKpiCard label="Month Profit" value={dashboard.data?.month_profit ?? "0.00"} /><AnalyticsKpiCard label="AOV" value={dashboard.data?.average_order_value ?? "0.00"} /></section><section className="grid gap-4 md:grid-cols-4"><AnalyticsKpiCard label="Month Ad Spend" value={advertising.data?.total_spend ?? "0.00"} /><AnalyticsKpiCard label="Month ROAS" value={advertising.data?.roas ?? "—"} /><AnalyticsKpiCard label="Month CPA" value={advertising.data?.average_cpa ?? "—"} /><AnalyticsKpiCard label="Month Advertising Profit" value={advertising.data?.total_net_profit ?? "—"} /><AnalyticsKpiCard label="Advertising ROI" value={advertising.data?.roi ? `${advertising.data.roi}%` : "—"} /></section><div className="grid gap-4 lg:grid-cols-2"><RevenueTrendChart data={dashboard.data?.sales_trend ?? []} /><TopProductsTable products={dashboard.data?.top_products ?? []} /></div></div></main>;
}
