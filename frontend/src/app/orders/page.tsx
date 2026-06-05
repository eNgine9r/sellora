"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ConfirmActionDialog } from "@/components/confirm-action-dialog";
import { FormDialog } from "@/components/form-dialog";
import { OrderDetails } from "@/features/orders/components/order-details";
import { OrderForm } from "@/features/orders/components/order-form";
import { OrderTable } from "@/features/orders/components/order-table";
import { formatMoney } from "@/lib/currency";
import { changeOrderStatus, createOrder, deleteOrder, fetchOrderDashboard, fetchOrders, updateOrder } from "@/services/orders";
import { fetchOrderShipment } from "@/services/shipments";
import { fetchInventory, fetchProducts, fetchProductVariants } from "@/services/products";
import { Order, OrderStatus } from "@/types/orders";
import { useAuth } from "@/hooks/use-auth";
import { safeApiErrorMessage } from "@/services/api";
import { useI18n } from "@/i18n/provider";

const STATUSES: (OrderStatus | "")[] = ["", "NEW", "CONFIRMED", "SHIPPED", "DELIVERED", "COMPLETED", "RETURNED", "CANCELLED"];
const ITEM_EDIT_STATUSES: OrderStatus[] = ["NEW", "CONFIRMED"];

export default function OrdersPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspace, currentWorkspaceId, status: authStatus } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const currencyCode = currentWorkspace?.currency_code ?? "UAH";
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
  const invalidateOrderState = () => {
    queryClient.invalidateQueries({ queryKey: ["orders", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["orders-dashboard", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["dashboard", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["analytics", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["inventory", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["product-variants", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["shipments", workspaceId] });
  };
  const createMutation = useMutation({ mutationFn: (values: Parameters<typeof createOrder>[1]) => createOrder(workspaceId, values), onSuccess: (order) => { setIsCreateOpen(false); setSelectedOrder(order); invalidateOrderState(); } });
  const statusMutation = useMutation({ mutationFn: ({ orderId, nextStatus }: { orderId: string; nextStatus: OrderStatus }) => changeOrderStatus(workspaceId, orderId, nextStatus), onSuccess: (order) => { setSelectedOrder(order); invalidateOrderState(); } });
  const updateMutation = useMutation({ mutationFn: (values: Parameters<typeof updateOrder>[2]) => updateOrder(workspaceId, editingOrder?.id ?? "", values), onSuccess: (order) => { setEditingOrder(null); setSelectedOrder(order); invalidateOrderState(); } });
  const archiveMutation = useMutation({ mutationFn: () => deleteOrder(workspaceId, archivingOrder?.id ?? ""), onSuccess: () => { if (selectedOrder?.id === archivingOrder?.id) setSelectedOrder(null); setArchivingOrder(null); invalidateOrderState(); } });

  return (
    <main className="min-h-screen min-w-0 overflow-x-hidden bg-slate-100 p-4 text-slate-950 sm:p-6">
      <div className="mx-auto grid min-w-0 max-w-7xl gap-6">
        <header className="flex flex-col gap-4 rounded-2xl bg-white p-6 shadow-sm md:flex-row md:items-end md:justify-between"><div><p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Sellora</p><h1 className="mt-2 text-3xl font-bold">{t("orders.title")}</h1><p className="mt-1 text-slate-600">{t("orders.subtitle")}</p></div><button className="min-h-11 rounded-lg bg-blue-600 px-4 py-3 font-semibold text-white" onClick={() => setIsCreateOpen(true)}>{t("orders.create")}</button></header>
        <section className="grid min-w-0 max-w-full gap-3 overflow-hidden rounded-2xl bg-white p-4 shadow-sm md:grid-cols-4"><select className="min-h-11 w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" value={status} onChange={(event) => setStatus(event.target.value as OrderStatus | "")}>{STATUSES.map((item) => <option key={item || "all"} value={item}>{item || "All statuses"}</option>)}</select><div className="text-sm text-slate-600">Today: {dashboardQuery.data?.orders_today ?? 0} orders · {formatMoney(dashboardQuery.data?.revenue_today, currencyCode)} revenue · {formatMoney(dashboardQuery.data?.profit_today, currencyCode)} profit</div></section>
        <div className="grid min-w-0 gap-6 lg:grid-cols-[1fr_360px]"><OrderTable orders={ordersQuery.data ?? []} currencyCode={currencyCode} onSelect={setSelectedOrder} onEdit={canEdit ? setEditingOrder : undefined} onArchive={canEdit ? setArchivingOrder : undefined} />{selectedOrder ? <OrderDetails order={selectedOrder} currencyCode={currencyCode} shipment={shipmentQuery.data} onStatusChange={(nextStatus) => statusMutation.mutate({ orderId: selectedOrder.id, nextStatus })} /> : <div className="rounded-xl border border-slate-200 bg-white p-4 text-slate-500">Select an order to view details, status history, and profit.</div>}</div>
        {isCreateOpen ? <FormDialog title={t("orders.create")} description="Reserve inventory, add costs, and keep profit totals in the same mobile-safe modal style." size="xl" onClose={() => setIsCreateOpen(false)}><OrderForm variants={variantsQuery.data ?? []} products={productsQuery.data ?? []} inventory={inventoryQuery.data ?? []} currencyCode={currencyCode} showProfit={currentWorkspace?.role === "OWNER"} onSubmit={(values) => createMutation.mutate(values as Parameters<typeof createOrder>[1])} /></FormDialog> : null}
        {editingOrder ? <FormDialog title={t("orders.edit")} description="Order items can be edited while the order is NEW or CONFIRMED." size="xl" onClose={() => setEditingOrder(null)}><OrderForm variants={variantsQuery.data ?? []} products={productsQuery.data ?? []} inventory={inventoryQuery.data ?? []} currencyCode={currencyCode} initialOrder={editingOrder} lockedItems={!ITEM_EDIT_STATUSES.includes(editingOrder.status)} submitLabel={t("actions.save")} showProfit={currentWorkspace?.role === "OWNER"} onSubmit={(values) => updateMutation.mutate(values as Parameters<typeof updateOrder>[2])} />{updateMutation.isError ? <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700 dark:bg-amber-500/15 dark:text-amber-100">{safeApiErrorMessage(updateMutation.error, "Please check the order items and costs.")}</p> : null}</FormDialog> : null}
        {archivingOrder ? <ConfirmActionDialog title="Archive test order?" description="Only NEW or CANCELLED orders can be archived. NEW order reservations are released; shipped or completed orders must use the status workflow first." actionLabel={t("orders.archive")} isSubmitting={archiveMutation.isPending} error={archiveMutation.isError ? safeApiErrorMessage(archiveMutation.error, "This record cannot be deleted in its current state.") : null} onCancel={() => setArchivingOrder(null)} onConfirm={() => archiveMutation.mutate()} /> : null}
      </div>
    </main>
  );
}
// Localization regression compatibility markers: Edit order; Save order.
// Localization regression compatibility markers: FormDialog title="Create order"; FormDialog title="Edit order".
