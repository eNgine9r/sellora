import { apiRequest } from "@/services/api";
import type { BankPaymentEvidenceLedger } from "@/types/bank-payment-evidence";

export function fetchBankPaymentEvidence(limit = 50): Promise<BankPaymentEvidenceLedger> {
  return apiRequest<BankPaymentEvidenceLedger>(`/finance/bank-evidence?limit=${limit}`);
}
