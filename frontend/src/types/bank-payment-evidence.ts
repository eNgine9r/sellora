export type BankPaymentRail = "BANK_IBAN" | "FOP_CARD" | "MONO_ACQUIRING_LINK" | "UNKNOWN_ACCOUNT_TRANSFER";
export type BankPaymentKind = "CUSTOMER_PAYMENT" | "UNCLASSIFIED_CREDIT" | "ACQUIRING_PAYOUT" | "REFUND";

export interface BankPaymentEvidence {
  id: string;
  provider: string;
  provider_account_id: string;
  external_reference: string;
  rail: BankPaymentRail;
  kind: BankPaymentKind;
  origin: "MANUAL_IMPORT" | "BANK_API" | "MERCHANT_API";
  amount_minor: number;
  currency: string;
  occurred_at: string;
  is_hold: boolean;
  invoice_id: string | null;
  order_number: string | null;
  candidate_order_id: string | null;
  review_reason: string;
}

export interface BankPaymentEvidenceLedger {
  rows: BankPaymentEvidence[];
  total_count: number;
}
