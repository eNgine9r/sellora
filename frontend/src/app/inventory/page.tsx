"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { EditRecordDialog } from "@/components/edit-record-dialog";
import { InventoryTable } from "@/features/inventory/components/inventory-table";
import { InventoryTransactionHistory } from "@/features/inventory/components/inventory-transaction-history";
import { createInventoryTransaction, fetchInventory, fetchInventoryTransactions, fetchProductVariants, updateInventory } from "@/services/products";
import { Inventory, InventoryTransactionType } from "@/types/products";
import { buildInventoryUpdatePayload } from "@/lib/payload-builders";
import { safeApiErrorMessage } from "@/services/api";
import { useAuth } from "@/hooks/use-auth";
import { cleanOptionalString } from "@/lib/payload-normalizers";

const TRANSACTION_TYPES: InventoryTransactionType[] = ["STOCK_IN", "STOCK_OUT", "RESERVE", "UNRESERVE", "RETURN", "ADJUSTMENT"];

export default function InventoryPage() {
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspaceId, status: authStatus } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [inventoryId, setInventoryId] = useState("");
  const [transactionType, setTransactionType] = useState<InventoryTransactionType>("STOCK_IN");
  const [quantity, setQuantity] = useState(1);
  const [reason, setReason] = useState("");
  const [editingInventory, setEditingInventory] = useState<Inventory | null>(null);
  const enabled = authStatus === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);

  const inventoryQuery = useQuery({ queryKey: ["inventory", workspaceId, lowStockOnly], queryFn: () => fetchInventory(workspaceId, lowStockOnly, undefined), enabled });
  const variantsQuery = useQuery({ queryKey: ["product-variants", workspaceId], queryFn: () => fetchProductVariants(workspaceId, undefined, undefined), enabled });
  const transactionsQuery = useQuery({ queryKey: ["inventory-transactions", workspaceId, inventoryId], queryFn: () => fetchInventoryTransactions(workspaceId, inventoryId || undefined, undefined), enabled });
  const transactionMutation = useMutation({ mutationFn: () => createInventoryTransaction(workspaceId, inventoryId, { transaction_type: transactionType, quantity: Math.max(1, quantity), reason: cleanOptionalString(reason) }, undefined), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["inventory", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["inventory-transactions", workspaceId] }); } });
  const updateMutation = useMutation({ mutationFn: (values: Record<string, string>) => updateInventory(workspaceId, editingInventory?.id ?? "", buildInventoryUpdatePayload(values), undefined), onSuccess: () => { setEditingInventory(null); queryClient.invalidateQueries({ queryKey: ["inventory", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["inventory-transactions", workspaceId] }); } });

  function submitTransaction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    transactionMutation.mutate();
  }

  return (
    <main className="min-h-screen bg-[#F8F7FC] p-4 sm:p-6 text-slate-950">
      <div className="mx-auto grid max-w-7xl gap-6">
        <header className="rounded-2xl bg-white p-6 shadow-sm"><p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Sellora Inventory</p><h1 className="mt-2 text-3xl font-bold">Inventory</h1><p className="mt-1 text-slate-600">Track stock levels, low stock, reservations, and inventory transaction history.</p></header>
        <section className="grid gap-3 rounded-2xl bg-white p-4 shadow-sm md:grid-cols-4">
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={lowStockOnly} onChange={(event) => setLowStockOnly(event.target.checked)} /> Low stock only</label>
          <select className="rounded-md border border-slate-300 px-3 py-2" value={inventoryId} onChange={(event) => setInventoryId(event.target.value)}><option value="">All inventory history</option>{(inventoryQuery.data ?? []).map((item) => <option key={item.id} value={item.id}>{item.product_variant_id}</option>)}</select>
        </section>
        <InventoryTable inventory={inventoryQuery.data ?? []} variants={variantsQuery.data ?? []} onEdit={setEditingInventory} />
        <form className="grid gap-3 rounded-2xl bg-white p-4 shadow-sm md:grid-cols-5" onSubmit={submitTransaction}>
          <select className="rounded-md border border-slate-300 px-3 py-2" required value={inventoryId} onChange={(event) => setInventoryId(event.target.value)}><option value="">Select inventory</option>{(inventoryQuery.data ?? []).map((item) => <option key={item.id} value={item.id}>{item.product_variant_id}</option>)}</select>
          <select className="rounded-md border border-slate-300 px-3 py-2" value={transactionType} onChange={(event) => setTransactionType(event.target.value as InventoryTransactionType)}>{TRANSACTION_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}</select>
          <input className="rounded-md border border-slate-300 px-3 py-2" min={1} type="number" value={quantity} onChange={(event) => setQuantity(Number(event.target.value))} />
          <input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Reason" value={reason} onChange={(event) => setReason(event.target.value)} />
          <button className="rounded-md bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700" type="submit">Record transaction</button>
        </form>
        <InventoryTransactionHistory transactions={transactionsQuery.data ?? []} />
        {editingInventory ? <EditRecordDialog title="Update inventory thresholds" fields={[{ name: "incoming_quantity", label: "Incoming quantity", type: "number" }, { name: "minimum_quantity", label: "Minimum quantity", type: "number" }]} initialValues={editingInventory} isSubmitting={updateMutation.isPending} submitError={updateMutation.isError ? safeApiErrorMessage(updateMutation.error, "Unable to save inventory changes. Please try again.") : null} onClose={() => setEditingInventory(null)} onSubmit={(values) => updateMutation.mutate(values)} /> : null}
      </div>
    </main>
  );
}
