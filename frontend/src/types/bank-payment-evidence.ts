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

export interface BankPreviewRow {
  provider_account_id: string;
  external_reference: string;
  rail: BankPaymentRail;
  kind: BankPaymentKind;
  amount_minor: number;
  status: "REVIEW" | "DUPLICATE";
  reason: string;
  candidate_order_id: string | null;
}

export interface BankEvidencePreview {
  rows: BankPreviewRow[];
  candidate_count: number;
  review_count: number;
  duplicate_count: number;
}

export interface BankEvidenceImportResult extends BankEvidencePreview {
  inserted_count: number;
}
