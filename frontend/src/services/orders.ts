import { apiRequest } from "@/services/api";
import { Order, OrderDashboard, OrderStatus, PaymentStatus } from "@/types/orders";

function workspaceHeaders(workspaceId?: string): HeadersInit {
  return workspaceId ? { "X-Workspace-ID": workspaceId } : {};
}

export type OrderCreatePayload = {
  customer_id: string | null;
  payment_status: PaymentStatus;
  items: { product_variant_id: string; quantity: number; unit_price: number; unit_cost: number }[];
  ad_cost: number;
  shipping_cost: number;
  cod_fee: number;
  other_cost: number;
  notes: string | null;
};

export async function fetchOrders(workspaceId: string, status?: OrderStatus | ""): Promise<Order[]> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const query = params.toString();
  return apiRequest<Order[]>(`/orders${query ? `?${query}` : ""}`, { headers: workspaceHeaders(workspaceId) });
}

export async function fetchOrderDashboard(workspaceId: string): Promise<OrderDashboard> {
  return apiRequest<OrderDashboard>("/orders/dashboard", { headers: workspaceHeaders(workspaceId) });
}

export async function createOrder(workspaceId: string, payload: OrderCreatePayload): Promise<Order> {
  return apiRequest<Order>("/orders", { method: "POST", headers: workspaceHeaders(workspaceId), body: JSON.stringify(payload) });
}

export async function changeOrderStatus(workspaceId: string, orderId: string, status: OrderStatus): Promise<Order> {
  return apiRequest<Order>(`/orders/${orderId}/status`, { method: "POST", headers: workspaceHeaders(workspaceId), body: JSON.stringify({ status }) });
}
