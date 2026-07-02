import { apiRequest } from "@/services/api";
import type { FinanceAdjustment, FinanceAdjustmentList, FinanceAdjustmentPayload, FinanceAdjustmentType, FinancePeriodComparison, FinanceSummary } from "@/types/finance";

function financeDateQuery(dateFrom: string, dateTo: string) {
  const params = new URLSearchParams();
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  return params;
}

export function fetchFinanceSummary(dateFrom: string, dateTo: string): Promise<FinanceSummary> {
  const params = financeDateQuery(dateFrom, dateTo);
  const query = params.toString();
  return apiRequest<FinanceSummary>(`/finance/summary${query ? `?${query}` : ""}`);
}

export function fetchFinanceTrends(dateFrom: string, dateTo: string): Promise<FinancePeriodComparison> {
  const params = financeDateQuery(dateFrom, dateTo);
  const query = params.toString();
  return apiRequest<FinancePeriodComparison>(`/finance/trends${query ? `?${query}` : ""}`);
}

export function fetchFinanceAdjustments(dateFrom: string, dateTo: string, type?: FinanceAdjustmentType): Promise<FinanceAdjustmentList> {
  const params = financeDateQuery(dateFrom, dateTo);
  if (type) params.set("type", type);
  params.set("limit", "100");
  const query = params.toString();
  return apiRequest<FinanceAdjustmentList>(`/finance/adjustments${query ? `?${query}` : ""}`);
}

export function createFinanceAdjustment(payload: FinanceAdjustmentPayload): Promise<FinanceAdjustment> {
  return apiRequest<FinanceAdjustment>("/finance/adjustments", { method: "POST", body: JSON.stringify(payload) });
}

export function updateFinanceAdjustment(id: string, payload: Partial<FinanceAdjustmentPayload>): Promise<FinanceAdjustment> {
  return apiRequest<FinanceAdjustment>(`/finance/adjustments/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function deleteFinanceAdjustment(id: string): Promise<void> {
  return apiRequest<void>(`/finance/adjustments/${id}`, { method: "DELETE" });
}
