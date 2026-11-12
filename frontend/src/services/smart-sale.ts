import { apiRequest } from "@/services/api";

export type SmartSaleCandidate = {
  document_id: string;
  tracking_masked: string;
  provider_status: string | null;
  state: "READY_FOR_REVIEW" | "NEEDS_INFO" | "CONFIRMED";
  conversation_id: string | null;
  customer_id: string | null;
  customer_instagram: string | null;
  price_hints: Array<{
    unit_price: string;
    message_id: string;
  }>;
  suggested_item: {
    variant_id: string;
    sku: string;
    product_name: string;
    quantity: number;
    suggested_unit_price: string;
    available_quantity: number | null;
    price_source: "CATALOG_SUGGESTION";
  } | null;
  reason: string;
  order_id: string | null;
};

export type SmartSaleResult = {
  document_id: string;
  order_id: string;
  customer_id: string;
  shipment_id: string;
  payment_status: "PAID";
  already_confirmed: boolean;
};

export function getSmartSaleCandidates(workspaceId: string): Promise<SmartSaleCandidate[]> {
  return apiRequest<SmartSaleCandidate[]>("/integrations/nova-poshta/external-documents/sale-candidates", {
    headers: { "X-Workspace-ID": workspaceId },
  });
}

export function confirmSmartSale(
  workspaceId: string,
  documentId: string,
  conversationId: string,
  variantId: string,
  quantity: number,
  price: string,
  selectionSource: "CATALOG_SUGGESTION" | "MANAGER_SELECTED",
): Promise<SmartSaleResult> {
  return apiRequest<SmartSaleResult>(`/integrations/nova-poshta/external-documents/${documentId}/confirm-sale`, {
    method: "POST",
    headers: { "X-Workspace-ID": workspaceId },
    body: JSON.stringify({
      expected_conversation_id: conversationId,
      product_variant_id: variantId,
      selection_source: selectionSource,
      quantity,
      unit_price: price,
      receipt_checked_in_direct: true,
      funds_received_in_bank: true,
      details_reviewed: true,
    }),
  });
}
