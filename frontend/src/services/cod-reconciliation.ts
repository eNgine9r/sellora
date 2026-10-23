import { apiRequest } from "@/services/api";
import type { CodImportResponse, CodImportRow, CodLedger, CodPreview } from "@/types/cod-reconciliation";

export function fetchCodLedger(from?: string, to?: string): Promise<CodLedger> {
  const params = new URLSearchParams();
  if (from) params.set("date_from", from);
  if (to) params.set("date_to", to);
  const query = params.toString();
  return apiRequest<CodLedger>("/finance/cod-reconciliation" + (query ? "?" + query : ""));
}

export function previewCodRegister(rows: CodImportRow[]): Promise<CodPreview> {
  return apiRequest<CodPreview>("/finance/cod-reconciliation/preview", {
    method: "POST", body: JSON.stringify({ rows }),
  });
}

export function importCodRegister(rows: CodImportRow[]): Promise<CodImportResponse> {
  return apiRequest<CodImportResponse>("/finance/cod-reconciliation/import", {
    method: "POST", body: JSON.stringify({ rows }),
  });
}
