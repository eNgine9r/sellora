export type OrderProposalCandidate = {
  product_id: string; variant_id: string; product_name: string; sku: string;
  color: string | null; size: string | null; price: string | number | null; available_quantity: number | null;
};
export type OrderProposalLine = {
  id: string; mention_text: string; quantity: number; source: "ANALYSIS_CONTEXT" | "INBOUND_SKU" | "INBOUND_PRODUCT";
  evidence: { message_id: string; snippet: string }[]; requires_review: boolean;
  match_status: "MATCHED" | "AMBIGUOUS" | "NOT_FOUND"; matched_by: string | null;
  reason: string; candidates_truncated: boolean; candidates: OrderProposalCandidate[];
};
export type DirectOrderProposal = {
  conversation_id: string; analysis_id: string | null; analysis_created_at: string | null;
  analysis_context_message_id: string | null;
  analysis_state: "MISSING" | "COMPLETED" | "STALE" | "FAILED" | "MALFORMED" | "PENDING";
  commercial_stage: "NONE" | "INTEREST" | "PRODUCT_QUESTION" | "PURCHASE_REQUEST";
  commercial_reason: string | null;
  catalog_truncated: boolean; context_truncated: boolean; lines: OrderProposalLine[];
};
export type ProposalItemSelection = { variantId: string; quantity: number; unitPrice: string };
