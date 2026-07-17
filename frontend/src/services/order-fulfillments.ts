import { apiRequest } from "@/services/api";
import { OrderFulfillmentPayload, OrderFulfillmentResult } from "@/types/order-fulfillment";

export function createOrderFulfillment(workspaceId: string, payload: OrderFulfillmentPayload) {
  return apiRequest<OrderFulfillmentResult>("/order-fulfillments", {
    method: "POST",
    headers: { "X-Workspace-ID": workspaceId },
    body: JSON.stringify(payload),
  });
}
