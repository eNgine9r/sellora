"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ConfirmActionDialog } from "@/components/confirm-action-dialog";
import { EditRecordDialog } from "@/components/edit-record-dialog";
import { OrderDetails } from "@/features/orders/components/order-details";
import { OrderForm } from "@/features/orders/components/order-form";
import { OrderTable } from "@/features/orders/components/order-table";
import { changeOrderStatus, createOrder, deleteOrder, fetchOrderDashboard, fetchOrders, updateOrder } from "@/services/orders";
import { fetchOrderShipment } from "@/services/shipments";
import { fetchInventory, fetchProducts, fetchProductVariants } from "@/services/products";
import { Order, OrderStatus } from "@/types/orders";
import { useAuth } from "@/hooks/use-auth";
import { buildOrderUpdatePayload } from "@/lib/payload-builders";
import { safeApiErrorMessage } from "@/services/api";

const STATUSES: (OrderStatus | "")[] = ["", "NEW", "CONFIRMED", "SHIPPED", "DELIVERED", "COMPLETED", "RETURNED", "CANCELLED"];

export default function OrdersPage() {
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspace, currentWorkspaceId, status: authStatus } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const [status, setStatus] = useState<OrderStatus | "">("");
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingOrder, setEditingOrder] = useState<Order | null>(null);
  const [archivingOrder, setArchivingOrder] = useState<Order | null>(null);
  const enabled = authStatus === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);
  const canEdit = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";

  const ordersQuery = useQuery({ queryKey: ["orders", workspaceId, status], queryFn: () => fetchOrders(workspaceId, status), enabled });
  const dashboardQuery = useQuery({ queryKey: ["orders-dashboard", workspaceId], queryFn: () => fetchOrderDashboard(workspaceId), enabled });
  const variantsQuery = useQuery({ queryKey: ["product-variants", workspaceId], queryFn: () => fetchProductVariants(workspaceId, undefined, undefined), enabled });
  const productsQuery = useQuery({ queryKey: ["products", workspaceId], queryFn: () => fetchProducts(workspaceId), enabled });
  const inventoryQuery = useQuery({ queryKey: ["inventory", workspaceId], queryFn: () => fetchInventory(workspaceId), enabled });
  const shipmentQuery = useQuery({ queryKey: ["order-shipment", workspaceId, selectedOrder?.id], queryFn: () => fetchOrderShipment(workspaceId, selectedOrder!.id), enabled: enabled && Boolean(selectedOrder) });
  const createMutation = useMutation({ mutationFn: (values: Parameters<typeof createOrder>[1]) => createOrder(workspaceId, values), onSuccess: (order) => { setIsCreateOpen(false); setSelectedOrder(order); queryClient.invalidateQueries({ queryKey: ["orders", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["orders-dashboard", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["analytics", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["inventory", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["product-variants", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["shipments", workspaceId] }); } });
  const statusMutation = useMutation({ mutationFn: ({ orderId, nextStatus }: { orderId: string; nextStatus: OrderStatus }) => changeOrderStatus(workspaceId, orderId, nextStatus), onSuccess: (order) => { setSelectedOrder(order); queryClient.invalidateQueries({ queryKey: ["orders", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["orders-dashboard", workspaceId] }); } });
  const updateMutation = useMutation({ mutationFn: (values: Record<string, string>) => updateOrder(workspaceId, editingOrder?.id ?? "", buildOrderUpdatePayload(values)), onSuccess: (order) => { setEditingOrder(null); setSelectedOrder(order); queryClient.invalidateQueries({ queryKey: ["orders", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["orders-dashboard", workspaceId] }); } });
  const archiveMutation = useMutation({ mutationFn: () => deleteOrder(workspaceId, archivingOrder?.id ?? ""), onSuccess: () => { if (selectedOrder?.id === archivingOrder?.id) setSelectedOrder(null); setArchivingOrder(null); queryClient.invalidateQueries({ queryKey: ["orders", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["orders-dashboard", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["inventory", workspaceId] }); } });

  return (
    <main className="min-h-screen bg-slate-100 p-4 sm:p-6 text-slate-950">
      <div className="mx-auto grid max-w-7xl gap-6">
        <header className="flex flex-col gap-4 rounded-2xl bg-white p-6 shadow-sm md:flex-row md:items-end md:justify-between"><div><p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Sellora Orders</p><h1 className="mt-2 text-3xl font-bold">Orders & Profit Engine</h1><p className="mt-1 text-slate-600">Create orders, reserve inventory, track status history, and inspect profit.</p></div><button className="min-h-11 rounded-lg bg-blue-600 px-4 py-3 font-semibold text-white" onClick={() => setIsCreateOpen(true)}>Create order</button></header>
        <section className="grid gap-3 rounded-2xl bg-white p-4 shadow-sm md:grid-cols-4"><select className="min-h-11 rounded-md border border-slate-300 px-3 py-2" value={status} onChange={(event) => setStatus(event.target.value as OrderStatus | "")}>{STATUSES.map((item) => <option key={item || "all"} value={item}>{item || "All statuses"}</option>)}</select><div className="text-sm text-slate-600">Today: {dashboardQuery.data?.orders_today ?? 0} orders · ${dashboardQuery.data?.revenue_today ?? "0"} revenue · ${dashboardQuery.data?.profit_today ?? "0"} profit</div></section>
        <div className="grid gap-6 lg:grid-cols-[1fr_360px]"><OrderTable orders={ordersQuery.data ?? []} onSelect={setSelectedOrder} onEdit={canEdit ? setEditingOrder : undefined} onArchive={canEdit ? setArchivingOrder : undefined} />{selectedOrder ? <OrderDetails order={selectedOrder} shipment={shipmentQuery.data} onStatusChange={(nextStatus) => statusMutation.mutate({ orderId: selectedOrder.id, nextStatus })} /> : <div className="rounded-xl border border-slate-200 bg-white p-4 text-slate-500">Select an order to view details, status history, and profit.</div>}</div>
        {isCreateOpen ? <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-slate-950/40 p-3 sm:p-4"><div className="w-full max-w-3xl overflow-hidden rounded-2xl bg-white p-4 shadow-xl sm:p-6"><div className="mb-4 flex items-center justify-between"><h2 className="text-xl font-bold">Create order</h2><button className="text-slate-500" onClick={() => setIsCreateOpen(false)}>Close</button></div><OrderForm variants={variantsQuery.data ?? []} products={productsQuery.data ?? []} inventory={inventoryQuery.data ?? []} showProfit={currentWorkspace?.role === "OWNER"} onSubmit={(values) => createMutation.mutate(values)} /></div></div> : null}
        {archivingOrder ? <ConfirmActionDialog title="Archive test order?" description="Only NEW or CANCELLED orders can be archived. NEW order reservations are released; shipped or completed orders must use the status workflow first." actionLabel="Archive order" isSubmitting={archiveMutation.isPending} error={archiveMutation.isError ? safeApiErrorMessage(archiveMutation.error, "This record cannot be deleted in its current state.") : null} onCancel={() => setArchivingOrder(null)} onConfirm={() => archiveMutation.mutate()} /> : null}
        {editingOrder ? <EditRecordDialog title="Edit order safe fields" fields={[{ name: "payment_status", label: "Payment status", type: "select", options: ["PENDING", "PAID", "COD", "REFUNDED"].map((value) => ({ value, label: value })) }, { name: "ad_cost", label: "Ad cost", type: "number" }, { name: "shipping_cost", label: "Shipping cost", type: "number" }, { name: "cod_fee", label: "COD fee", type: "number" }, { name: "other_cost", label: "Other cost", type: "number" }, { name: "notes", label: "Notes", type: "textarea" }]} initialValues={editingOrder} isSubmitting={updateMutation.isPending} submitError={updateMutation.isError ? safeApiErrorMessage(updateMutation.error, "Unable to save order changes. Please try again.") : null} onClose={() => setEditingOrder(null)} onSubmit={(values) => updateMutation.mutate(values)} /> : null}
      </div>
    </main>
  );
}
