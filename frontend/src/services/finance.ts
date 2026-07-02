import { apiRequest } from "@/services/api";
import type { FinanceSummary } from "@/types/finance";

export function fetchFinanceSummary(dateFrom: string, dateTo: string): Promise<FinanceSummary> {
  const params = new URLSearchParams();
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  const query = params.toString();
  return apiRequest<FinanceSummary>(`/finance/summary${query ? `?${query}` : ""}`);
}
