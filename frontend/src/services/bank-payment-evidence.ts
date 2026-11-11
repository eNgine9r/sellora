import { apiRequest } from "@/services/api";
import type { BankPaymentEvidenceLedger } from "@/types/bank-payment-evidence";

export function fetchBankPaymentEvidence(limit = 50): Promise<BankPaymentEvidenceLedger> {
  return apiRequest<BankPaymentEvidenceLedger>(`/finance/bank-evidence?limit=${limit}`);
}

import type { BankImportRow } from "@/lib/bank-payment-evidence-csv";
import type { BankEvidenceImportResult, BankEvidencePreview } from "@/types/bank-payment-evidence";

export function previewBankEvidence(rows: BankImportRow[]): Promise<BankEvidencePreview> {
  return apiRequest<BankEvidencePreview>("/finance/bank-evidence/preview", {
    method: "POST", body: JSON.stringify({ rows }),
  });
}

export function importBankEvidence(rows: BankImportRow[]): Promise<BankEvidenceImportResult> {
  return apiRequest<BankEvidenceImportResult>("/finance/bank-evidence/import", {
    method: "POST", body: JSON.stringify({ rows }),
  });
}
