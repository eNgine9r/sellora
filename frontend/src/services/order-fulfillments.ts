import { apiRequest } from "@/services/api";
import { FulfillmentExecuteResult, FulfillmentRequest, FulfillmentStatus, FulfillmentPrepareResult, OrderFulfillmentPayload, OrderFulfillmentResult } from "@/types/order-fulfillment";

export function createOrderFulfillment(workspaceId: string, payload: OrderFulfillmentPayload) {
  return apiRequest<OrderFulfillmentResult>("/order-fulfillments", {
    method: "POST",
    headers: { "X-Workspace-ID": workspaceId },
    body: JSON.stringify(payload),
  });
}

export function prepareOrderFulfillment(workspaceId: string, orderId: string, payload: FulfillmentRequest) {
  return apiRequest<FulfillmentPrepareResult>(`/orders/${orderId}/fulfillment/prepare`, {
    method: "POST",
    headers: { "X-Workspace-ID": workspaceId },
    body: JSON.stringify(payload),
  });
}

export function executeOrderFulfillment(workspaceId: string, orderId: string, payload: FulfillmentRequest & { create_provider_document: boolean }, idempotencyKey: string) {
  return apiRequest<FulfillmentExecuteResult>(`/orders/${orderId}/fulfillment/execute`, {
    method: "POST",
    headers: { "X-Workspace-ID": workspaceId, "Idempotency-Key": idempotencyKey },
    body: JSON.stringify(payload),
  });
}

export function getOrderFulfillmentStatus(workspaceId: string, orderId: string) {
  return apiRequest<FulfillmentStatus>(`/orders/${orderId}/fulfillment`, {
    headers: { "X-Workspace-ID": workspaceId },
  });
}

export function reconcileOrderFulfillment(workspaceId: string, orderId: string) {
  return apiRequest<FulfillmentExecuteResult>(`/orders/${orderId}/fulfillment/reconcile`, {
    method: "POST",
    headers: { "X-Workspace-ID": workspaceId },
  });
}

export function cancelOrderFulfillment(workspaceId: string, orderId: string, payload: { cancel_local_operation: boolean; cancel_provider_document: boolean; release_inventory: boolean; reason: string | null }) {
  return apiRequest<FulfillmentStatus>(`/orders/${orderId}/fulfillment/cancel`, {
    method: "POST",
    headers: { "X-Workspace-ID": workspaceId },
    body: JSON.stringify(payload),
  });
}
