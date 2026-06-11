import { apiRequest } from "@/services/api";
import { AdvertisingReport, BusinessInsightsResponse, CustomersReport, CustomersSummary, DashboardAnalytics, DashboardSummary, InventoryReport, InventorySummary, ProductsReport, ProfitSummary, SalesReport, SalesSummary, SalesTrendItem, TopProduct } from "@/types/analytics";

function authHeaders(workspaceId?: string, token?: string) {
  return { ...(workspaceId ? { "X-Workspace-ID": workspaceId } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) };
}


function reportRangeQuery(dateFrom?: string, dateTo?: string) {
  const params = new URLSearchParams();
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  const query = params.toString();
  return query ? `?${query}` : "";
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


export const fetchSalesReport = (workspaceId: string, token?: string, dateFrom?: string, dateTo?: string) => apiRequest<SalesReport>(`/analytics/sales-report${reportRangeQuery(dateFrom, dateTo)}`, { headers: authHeaders(workspaceId, token) });
export const fetchProductsReport = (workspaceId: string, token?: string, dateFrom?: string, dateTo?: string) => apiRequest<ProductsReport>(`/analytics/products-report${reportRangeQuery(dateFrom, dateTo)}`, { headers: authHeaders(workspaceId, token) });
export const fetchAdvertisingReport = (workspaceId: string, token?: string, dateFrom?: string, dateTo?: string) => apiRequest<AdvertisingReport>(`/analytics/advertising-report${reportRangeQuery(dateFrom, dateTo)}`, { headers: authHeaders(workspaceId, token) });
export const fetchCustomersReport = (workspaceId: string, token?: string, dateFrom?: string, dateTo?: string) => apiRequest<CustomersReport>(`/analytics/customers-report${reportRangeQuery(dateFrom, dateTo)}`, { headers: authHeaders(workspaceId, token) });
export const fetchInventoryReport = (workspaceId: string, token?: string, dateFrom?: string, dateTo?: string) => apiRequest<InventoryReport>(`/analytics/inventory-report${reportRangeQuery(dateFrom, dateTo)}`, { headers: authHeaders(workspaceId, token) });
export const fetchBusinessInsights = (workspaceId: string, token?: string, dateFrom?: string, dateTo?: string) => apiRequest<BusinessInsightsResponse>(`/analytics/business-insights${reportRangeQuery(dateFrom, dateTo)}`, { headers: authHeaders(workspaceId, token) });
export const fetchDashboardSummary = (workspaceId: string, token?: string, dateFrom?: string, dateTo?: string) => apiRequest<DashboardSummary>(`/analytics/dashboard-summary${reportRangeQuery(dateFrom, dateTo)}`, { headers: authHeaders(workspaceId, token) });
