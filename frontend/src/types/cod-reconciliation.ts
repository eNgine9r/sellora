export type CodImportSource = "NOVAPAY_REGISTER" | "BANK_STATEMENT";
export type CodImportRow = {
  source: CodImportSource;
  reference: string;
  tracking_number: string | null;
  gross_amount: string;
  fee_amount: string;
  paid_at: string;
};
export type CodReviewRow = {
  reference: string;
  tracking_number: string | null;
  amount: string;
  status: "MATCHED" | "REVIEW" | "DUPLICATE";
  reason: string | null;
  order_id: string | null;
};
export type CodPreview = {
  rows: CodReviewRow[];
  matched_count: number;
  review_count: number;
  duplicate_count: number;
};
export type CodImportResponse = CodPreview & { inserted_count: number };
export type CodLedger = {
  rows: Array<{
    id: string;
    source: CodImportSource;
    reference: string;
    tracking_number: string | null;
    order_id: string | null;
    gross_amount: string;
    fee_amount: string;
    paid_at: string;
    status: "MATCHED" | "REVIEW";
    review_reason: string | null;
  }>;
  matched_receipts: string;
  review_receipts: string;
  pending_historical_amount: string;
  historical_amount_unverified_count: number;
  unvalued_historical_orders: number;
  matched_count: number;
  review_count: number;
};
