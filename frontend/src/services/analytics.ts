import { apiRequest } from "@/services/api";
import { CustomersSummary, DashboardAnalytics, InventorySummary, ProfitSummary, SalesSummary, SalesTrendItem, TopProduct } from "@/types/analytics";

function authHeaders(workspaceId: string, token?: string) {
  return { "X-Workspace-ID": workspaceId, ...(token ? { Authorization: `Bearer ${token}` } : {}) };
}

function rangeQuery(startDate?: string, endDate?: string, extra?: Record<string, string | number | undefined>) {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  Object.entries(extra ?? {}).forEach(([key, value]) => { if (value !== undefined) params.set(key, String(value)); });
  const query = params.toString();
  return query ? `?${query}` : "";
}

export const fetchSalesSummary = (workspaceId: string, token?: string, startDate?: string, endDate?: string) => apiRequest<SalesSummary>(`/analytics/sales-summary${rangeQuery(startDate, endDate)}`, { headers: authHeaders(workspaceId, token) });
export const fetchProfitSummary = (workspaceId: string, token?: string, startDate?: string, endDate?: string) => apiRequest<ProfitSummary>(`/analytics/profit-summary${rangeQuery(startDate, endDate)}`, { headers: authHeaders(workspaceId, token) });
export const fetchSalesTrend = (workspaceId: string, token?: string, startDate?: string, endDate?: string) => apiRequest<SalesTrendItem[]>(`/analytics/sales-trend${rangeQuery(startDate, endDate)}`, { headers: authHeaders(workspaceId, token) });
export const fetchTopProducts = (workspaceId: string, token?: string, startDate?: string, endDate?: string, limit = 10) => apiRequest<TopProduct[]>(`/analytics/top-products${rangeQuery(startDate, endDate, { limit })}`, { headers: authHeaders(workspaceId, token) });
export const fetchCustomersSummary = (workspaceId: string, token?: string, startDate?: string, endDate?: string) => apiRequest<CustomersSummary>(`/analytics/customers-summary${rangeQuery(startDate, endDate)}`, { headers: authHeaders(workspaceId, token) });
export const fetchInventorySummary = (workspaceId: string, token?: string) => apiRequest<InventorySummary>("/analytics/inventory-summary", { headers: authHeaders(workspaceId, token) });
export const fetchAnalyticsDashboard = (workspaceId: string, token?: string) => apiRequest<DashboardAnalytics>("/analytics/dashboard", { headers: authHeaders(workspaceId, token) });
