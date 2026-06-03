"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { AnalyticsKpiCard } from "@/features/analytics/components/analytics-kpi-card";
import { DateRangeFilter } from "@/features/analytics/components/date-range-filter";
import { LowStockTable } from "@/features/analytics/components/low-stock-table";
import { OrdersTrendChart } from "@/features/analytics/components/orders-trend-chart";
import { ProfitTrendChart } from "@/features/analytics/components/profit-trend-chart";
import { RevenueTrendChart } from "@/features/analytics/components/revenue-trend-chart";
import { TopCustomersTable } from "@/features/analytics/components/top-customers-table";
import { TopProductsTable } from "@/features/analytics/components/top-products-table";
import { fetchCustomersSummary, fetchInventorySummary, fetchProfitSummary, fetchSalesSummary, fetchSalesTrend, fetchTopProducts } from "@/services/analytics";

export default function AnalyticsPage() {
  const [workspaceId, setWorkspaceId] = useState("");
  const [token, setToken] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const enabled = Boolean(workspaceId);
  const sales = useQuery({ queryKey: ["analytics-sales", workspaceId, startDate, endDate], queryFn: () => fetchSalesSummary(workspaceId, token, startDate, endDate), enabled });
  const profit = useQuery({ queryKey: ["analytics-profit", workspaceId, startDate, endDate], queryFn: () => fetchProfitSummary(workspaceId, token, startDate, endDate), enabled });
  const trend = useQuery({ queryKey: ["analytics-trend", workspaceId, startDate, endDate], queryFn: () => fetchSalesTrend(workspaceId, token, startDate, endDate), enabled });
  const products = useQuery({ queryKey: ["analytics-products", workspaceId, startDate, endDate], queryFn: () => fetchTopProducts(workspaceId, token, startDate, endDate), enabled });
  const customers = useQuery({ queryKey: ["analytics-customers", workspaceId, startDate, endDate], queryFn: () => fetchCustomersSummary(workspaceId, token, startDate, endDate), enabled });
  const inventory = useQuery({ queryKey: ["analytics-inventory", workspaceId], queryFn: () => fetchInventorySummary(workspaceId, token), enabled });

  return <main className="min-h-screen bg-slate-100 p-6 text-slate-950"><div className="mx-auto grid max-w-7xl gap-6"><header className="rounded-2xl bg-white p-6 shadow-sm"><p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Sellora Analytics</p><h1 className="mt-2 text-3xl font-bold">Analytics Engine</h1><p className="mt-1 text-slate-600">Sales, profit, products, customers, and inventory insights.</p></header><section className="grid gap-3 rounded-2xl bg-white p-4 shadow-sm md:grid-cols-2"><input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Workspace ID" value={workspaceId} onChange={(event) => setWorkspaceId(event.target.value)} /><input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Access token" value={token} onChange={(event) => setToken(event.target.value)} /></section><DateRangeFilter startDate={startDate} endDate={endDate} onStartDateChange={setStartDate} onEndDateChange={setEndDate} /><section><h2 className="mb-3 text-xl font-bold">Sales</h2><div className="grid gap-4 md:grid-cols-4"><AnalyticsKpiCard label="Total Orders" value={sales.data?.total_orders ?? 0} /><AnalyticsKpiCard label="Revenue" value={sales.data?.total_revenue ?? "0.00"} /><AnalyticsKpiCard label="AOV" value={sales.data?.average_order_value ?? "0.00"} /><AnalyticsKpiCard label="Completed" value={sales.data?.completed_orders ?? 0} /></div><div className="mt-4 grid gap-4 lg:grid-cols-2"><RevenueTrendChart data={trend.data ?? []} /><OrdersTrendChart data={trend.data ?? []} /></div></section><section><h2 className="mb-3 text-xl font-bold">Profit</h2><div className="grid gap-4 md:grid-cols-4"><AnalyticsKpiCard label="Net Profit" value={profit.data?.total_net_profit ?? "Restricted"} /><AnalyticsKpiCard label="Margin %" value={profit.data?.margin_percent ?? "Restricted"} /><AnalyticsKpiCard label="Product Cost" value={profit.data?.total_product_cost ?? "Restricted"} /><AnalyticsKpiCard label="Other Costs" value={profit.data?.total_other_cost ?? "Restricted"} /></div><div className="mt-4"><ProfitTrendChart data={trend.data ?? []} /></div></section><section><h2 className="mb-3 text-xl font-bold">Products</h2><TopProductsTable products={products.data ?? []} /></section><section><h2 className="mb-3 text-xl font-bold">Customers</h2><div className="mb-4 grid gap-4 md:grid-cols-4"><AnalyticsKpiCard label="Total Customers" value={customers.data?.total_customers ?? 0} /><AnalyticsKpiCard label="New Customers" value={customers.data?.new_customers ?? 0} /><AnalyticsKpiCard label="Repeat Customers" value={customers.data?.repeat_customers ?? 0} /><AnalyticsKpiCard label="Repeat Rate" value={customers.data?.repeat_purchase_rate ?? "0.00"} /></div><TopCustomersTable customers={customers.data?.top_customers ?? []} /></section><section><h2 className="mb-3 text-xl font-bold">Inventory</h2><div className="mb-4 grid gap-4 md:grid-cols-4"><AnalyticsKpiCard label="Total Variants" value={inventory.data?.total_variants ?? 0} /><AnalyticsKpiCard label="Low Stock" value={inventory.data?.low_stock_count ?? 0} /><AnalyticsKpiCard label="Out of Stock" value={inventory.data?.out_of_stock_count ?? 0} /><AnalyticsKpiCard label="Stock Units" value={inventory.data?.total_stock_units ?? 0} /></div><LowStockTable items={inventory.data?.low_stock_items ?? []} /></section></div></main>;
}
