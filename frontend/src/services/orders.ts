import { apiRequest } from "@/services/api";
import { Order, OrderDashboard, OrderStatus, PaymentStatus } from "@/types/orders";

function workspaceHeaders(workspaceId: string, token?: string): HeadersInit {
  return {
    "X-Workspace-ID": workspaceId,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export type OrderCreatePayload = {
  customer_id?: string;
  payment_status: PaymentStatus;
  items: { product_variant_id: string; quantity: number; unit_price: string; unit_cost?: string }[];
  ad_cost?: string;
  shipping_cost?: string;
  cod_fee?: string;
  other_cost?: string;
  notes?: string;
};

export async function fetchOrders(workspaceId: string, status?: OrderStatus | "", token?: string): Promise<Order[]> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const query = params.toString();
  return apiRequest<Order[]>(`/orders${query ? `?${query}` : ""}`, { headers: workspaceHeaders(workspaceId, token) });
}

export async function fetchOrderDashboard(workspaceId: string, token?: string): Promise<OrderDashboard> {
  return apiRequest<OrderDashboard>("/orders/dashboard", { headers: workspaceHeaders(workspaceId, token) });
}

export async function createOrder(workspaceId: string, payload: OrderCreatePayload, token?: string): Promise<Order> {
  return apiRequest<Order>("/orders", { method: "POST", headers: workspaceHeaders(workspaceId, token), body: JSON.stringify(payload) });
}

export async function changeOrderStatus(workspaceId: string, orderId: string, status: OrderStatus, token?: string): Promise<Order> {
  return apiRequest<Order>(`/orders/${orderId}/status`, { method: "POST", headers: workspaceHeaders(workspaceId, token), body: JSON.stringify({ status }) });
}
