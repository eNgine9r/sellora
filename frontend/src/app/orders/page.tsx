"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { OrderDetails } from "@/features/orders/components/order-details";
import { OrderForm } from "@/features/orders/components/order-form";
import { OrderTable } from "@/features/orders/components/order-table";
import { changeOrderStatus, createOrder, fetchOrderDashboard, fetchOrders } from "@/services/orders";
import { fetchProductVariants } from "@/services/products";
import { Order, OrderStatus } from "@/types/orders";
import { useAuth } from "@/hooks/use-auth";

const STATUSES: (OrderStatus | "")[] = ["", "NEW", "CONFIRMED", "SHIPPED", "DELIVERED", "COMPLETED", "RETURNED", "CANCELLED"];

export default function OrdersPage() {
  const queryClient = useQueryClient();
  const { currentWorkspaceId } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const [status, setStatus] = useState<OrderStatus | "">("");
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const enabled = Boolean(workspaceId);

  const ordersQuery = useQuery({ queryKey: ["orders", workspaceId, status], queryFn: () => fetchOrders(workspaceId, status, undefined), enabled });
  const dashboardQuery = useQuery({ queryKey: ["orders-dashboard", workspaceId], queryFn: () => fetchOrderDashboard(workspaceId, undefined), enabled });
  const variantsQuery = useQuery({ queryKey: ["product-variants", workspaceId], queryFn: () => fetchProductVariants(workspaceId, undefined, undefined), enabled });
  const createMutation = useMutation({ mutationFn: (values: Parameters<typeof createOrder>[1]) => createOrder(workspaceId, values, undefined), onSuccess: () => { setIsCreateOpen(false); queryClient.invalidateQueries({ queryKey: ["orders", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["orders-dashboard", workspaceId] }); } });
  const statusMutation = useMutation({ mutationFn: ({ orderId, nextStatus }: { orderId: string; nextStatus: OrderStatus }) => changeOrderStatus(workspaceId, orderId, nextStatus, undefined), onSuccess: (order) => { setSelectedOrder(order); queryClient.invalidateQueries({ queryKey: ["orders", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["orders-dashboard", workspaceId] }); } });

  return (
    <main className="min-h-screen bg-slate-100 p-6 text-slate-950">
      <div className="mx-auto grid max-w-7xl gap-6">
        <header className="flex flex-col gap-4 rounded-2xl bg-white p-6 shadow-sm md:flex-row md:items-end md:justify-between"><div><p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Sellora Orders</p><h1 className="mt-2 text-3xl font-bold">Orders & Profit Engine</h1><p className="mt-1 text-slate-600">Create orders, reserve inventory, track status history, and inspect profit.</p></div><button className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white" onClick={() => setIsCreateOpen(true)}>Create order</button></header>
        <section className="grid gap-3 rounded-2xl bg-white p-4 shadow-sm md:grid-cols-4"><select className="rounded-md border border-slate-300 px-3 py-2" value={status} onChange={(event) => setStatus(event.target.value as OrderStatus | "")}>{STATUSES.map((item) => <option key={item || "all"} value={item}>{item || "All statuses"}</option>)}</select><div className="text-sm text-slate-600">Today: {dashboardQuery.data?.orders_today ?? 0} orders · ${dashboardQuery.data?.revenue_today ?? "0"} revenue · ${dashboardQuery.data?.profit_today ?? "0"} profit</div></section>
        <div className="grid gap-6 lg:grid-cols-[1fr_360px]"><OrderTable orders={ordersQuery.data ?? []} onSelect={setSelectedOrder} />{selectedOrder ? <OrderDetails order={selectedOrder} onStatusChange={(nextStatus) => statusMutation.mutate({ orderId: selectedOrder.id, nextStatus })} /> : <div className="rounded-xl border border-slate-200 bg-white p-4 text-slate-500">Select an order to view details, status history, and profit.</div>}</div>
        {isCreateOpen ? <div className="fixed inset-0 grid place-items-center bg-slate-950/40 p-4"><div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl"><div className="mb-4 flex items-center justify-between"><h2 className="text-xl font-bold">Create order</h2><button className="text-slate-500" onClick={() => setIsCreateOpen(false)}>Close</button></div><OrderForm variants={variantsQuery.data ?? []} onSubmit={(values) => createMutation.mutate(values)} /></div></div> : null}
      </div>
    </main>
  );
}
