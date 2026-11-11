import { apiRequest } from "@/services/api";

export type ManualPaymentMethod = "BANK_IBAN" | "FOP_CARD" | "MONO_ACQUIRING_LINK";

export interface ManualPaymentVerification {
  id: string;
  order_id: string;
  payment_method: ManualPaymentMethod;
  amount_minor: number;
  currency: string;
  receipt_checked: boolean;
  bank_received_checked: boolean;
  receipt_note: string | null;
  verified_by_user_id: string | null;
  verified_at: string;
  reference_suffix: string;
}

export type ManualPaymentRequest = {
  payment_method: ManualPaymentMethod;
  transaction_reference: string;
  amount_minor: number;
  receipt_checked: boolean;
  bank_received_checked: boolean;
  receipt_note: string | null;
};

export interface ManualPaymentResult {
  confirmation: ManualPaymentVerification;
  payment_status: string;
}

export function getManualPaymentVerification(workspaceId: string, orderId: string): Promise<ManualPaymentVerification | null> {
  return apiRequest<ManualPaymentVerification | null>(`/orders/${orderId}/manual-payment`, {
    headers: { "X-Workspace-ID": workspaceId },
  });
}

export function confirmManualOrderPayment(workspaceId: string, orderId: string, payload: ManualPaymentRequest): Promise<ManualPaymentResult> {
  return apiRequest<ManualPaymentResult>(`/orders/${orderId}/manual-payment/confirm`, {
    method: "POST",
    headers: { "X-Workspace-ID": workspaceId },
    body: JSON.stringify(payload),
  });
}
