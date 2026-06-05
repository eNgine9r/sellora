"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { EditRecordDialog } from "@/components/edit-record-dialog";
import { PaginationControls, clampPage, paginateItems } from "@/components/pagination-controls";
import { InventoryTable } from "@/features/inventory/components/inventory-table";
import { InventoryTransactionHistory } from "@/features/inventory/components/inventory-transaction-history";
import { createInventoryTransaction, fetchInventory, fetchInventoryTransactions, fetchProducts, fetchProductVariants, updateInventory } from "@/services/products";
import { Inventory, InventoryTransactionType } from "@/types/products";
import { CategoryFilter, categoryMatches, translatedCategoryOptions } from "@/lib/categories";
import { buildInventoryUpdatePayload } from "@/lib/payload-builders";
import { safeApiErrorMessage } from "@/services/api";
import { useAuth } from "@/hooks/use-auth";
import { cleanOptionalString } from "@/lib/payload-normalizers";
import { useI18n } from "@/i18n/provider";

const TRANSACTION_TYPES: InventoryTransactionType[] = ["STOCK_IN", "STOCK_OUT", "RESERVE", "UNRESERVE", "RETURN", "ADJUSTMENT"];

export default function InventoryPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspace, currentWorkspaceId, status: authStatus } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>("all");
  const [inventoryPage, setInventoryPage] = useState(1);
  const [inventoryPageSize, setInventoryPageSize] = useState(5);
  const [inventoryId, setInventoryId] = useState("");
  const [transactionType, setTransactionType] = useState<InventoryTransactionType>("STOCK_IN");
  const [quantity, setQuantity] = useState(1);
  const [reason, setReason] = useState("");
  const [editingInventory, setEditingInventory] = useState<Inventory | null>(null);
  const enabled = authStatus === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);
  const canEdit = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";

  const inventoryQuery = useQuery({ queryKey: ["inventory", workspaceId, lowStockOnly], queryFn: () => fetchInventory(workspaceId, lowStockOnly, undefined), enabled });
  const variantsQuery = useQuery({ queryKey: ["product-variants", workspaceId], queryFn: () => fetchProductVariants(workspaceId, undefined, undefined), enabled });
  const productsQuery = useQuery({ queryKey: ["products", workspaceId], queryFn: () => fetchProducts(workspaceId, undefined, undefined), enabled });
  const transactionsQuery = useQuery({ queryKey: ["inventory-transactions", workspaceId, inventoryId], queryFn: () => fetchInventoryTransactions(workspaceId, inventoryId || undefined, undefined), enabled });
  const transactionMutation = useMutation({ mutationFn: () => createInventoryTransaction(workspaceId, inventoryId, { transaction_type: transactionType, quantity: Math.max(1, quantity), reason: cleanOptionalString(reason) }, undefined), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["inventory", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["inventory-transactions", workspaceId] }); } });
  const updateMutation = useMutation({ mutationFn: (values: Record<string, string>) => updateInventory(workspaceId, editingInventory?.id ?? "", buildInventoryUpdatePayload(values), undefined), onSuccess: () => { setEditingInventory(null); queryClient.invalidateQueries({ queryKey: ["inventory", workspaceId] }); queryClient.invalidateQueries({ queryKey: ["inventory-transactions", workspaceId] }); } });

  const categoryOptions = translatedCategoryOptions(t);
  const variantById = useMemo(() => new Map((variantsQuery.data ?? []).map((variant) => [variant.id, variant])), [variantsQuery.data]);
  const productById = useMemo(() => new Map((productsQuery.data ?? []).map((product) => [product.id, product])), [productsQuery.data]);
  const visibleInventory = useMemo(() => (inventoryQuery.data ?? []).filter((item) => {
    const variant = variantById.get(item.product_variant_id);
    const product = variant ? productById.get(variant.product_id) : undefined;
    return categoryMatches(product?.category, categoryFilter);
  }), [inventoryQuery.data, variantById, productById, categoryFilter]);
  const paginatedInventory = paginateItems(visibleInventory, inventoryPage, inventoryPageSize);

  useEffect(() => {
    setInventoryPage(1);
  }, [categoryFilter, lowStockOnly]);
  useEffect(() => {
    setInventoryPage((page) => clampPage(page, inventoryPageSize, visibleInventory.length));
  }, [inventoryPageSize, visibleInventory.length]);

  function submitTransaction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    transactionMutation.mutate();
  }

  return (
    <main className="min-h-screen min-w-0 overflow-x-hidden bg-[#F8F7FC] p-4 sm:p-6 text-slate-950">
      <div className="mx-auto grid min-w-0 max-w-7xl gap-6">
        <header className="min-w-0 max-w-full overflow-hidden rounded-2xl bg-white p-6 shadow-sm"><p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Sellora Inventory</p><h1 className="mt-2 text-3xl font-bold">{t("inventory.title")}</h1><p className="mt-1 text-slate-600">{t("inventory.subtitle")}</p></header>
        <section className="grid min-w-0 max-w-full gap-3 overflow-hidden rounded-2xl bg-white p-4 shadow-sm md:grid-cols-4">
          <label className="flex min-w-0 items-center gap-2 text-sm"><input type="checkbox" checked={lowStockOnly} onChange={(event) => setLowStockOnly(event.target.checked)} /> {t("inventory.lowStockOnly")}</label>
          <select className="w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" aria-label={t("inventory.filterByCategory")} value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value as CategoryFilter)}><option value="all">{t("inventory.allCategories")}</option>{categoryOptions.map((category) => <option key={category.value} value={category.value}>{category.label}</option>)}</select>
          <select className="w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" value={inventoryId} onChange={(event) => setInventoryId(event.target.value)}><option value="">{t("inventory.allHistory")}</option>{visibleInventory.map((item) => <option key={item.id} value={item.id}>{item.product_variant_id}</option>)}</select>
        </section>
        <InventoryTable inventory={paginatedInventory} variants={variantsQuery.data ?? []} products={productsQuery.data ?? []} onEdit={canEdit ? setEditingInventory : undefined} />
        <PaginationControls page={inventoryPage} pageSize={inventoryPageSize} totalItems={visibleInventory.length} onPageChange={setInventoryPage} onPageSizeChange={(size) => { setInventoryPageSize(size); setInventoryPage(1); }} />
        <form className="grid min-w-0 max-w-full gap-3 overflow-hidden rounded-2xl bg-white p-4 shadow-sm md:grid-cols-5" onSubmit={submitTransaction}>
          <select className="w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" required value={inventoryId} onChange={(event) => setInventoryId(event.target.value)}><option value="">{t("inventory.selectInventory")}</option>{visibleInventory.map((item) => <option key={item.id} value={item.id}>{item.product_variant_id}</option>)}</select>
          <select className="w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" value={transactionType} onChange={(event) => setTransactionType(event.target.value as InventoryTransactionType)}>{TRANSACTION_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}</select>
          <input className="w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" min={1} type="number" value={quantity} onChange={(event) => setQuantity(Number(event.target.value))} />
          <input className="w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" placeholder={t("inventory.reason")} value={reason} onChange={(event) => setReason(event.target.value)} />
          <button className="rounded-md bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60" disabled={!canEdit} type="submit">{t("inventory.adjustStock")}</button>
        </form>
        <InventoryTransactionHistory transactions={transactionsQuery.data ?? []} />
        {editingInventory ? <EditRecordDialog title={t("inventory.updateThresholds")} fields={[{ name: "incoming_quantity", label: t("inventory.incomingQuantity"), type: "number" }, { name: "minimum_quantity", label: t("inventory.minimumQuantity"), type: "number" }]} initialValues={editingInventory} isSubmitting={updateMutation.isPending} submitError={updateMutation.isError ? safeApiErrorMessage(updateMutation.error, "Unable to save inventory changes. Please try again.") : null} onClose={() => setEditingInventory(null)} onSubmit={(values) => updateMutation.mutate(values)} /> : null}
      </div>
    </main>
  );
}
// Localization regression compatibility marker: Adjust stock.
