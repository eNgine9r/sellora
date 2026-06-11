"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { EditRecordDialog } from "@/components/edit-record-dialog";
import { FilterBar, ResetFiltersButton, SearchInput, SortSelect } from "@/components/filter-controls";
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
  const [inventorySearch, setInventorySearch] = useState("");
  const [inventorySort, setInventorySort] = useState("stockDesc");
  const [historyTypeFilter, setHistoryTypeFilter] = useState<InventoryTransactionType | "all">("all");
  const [transactionPage, setTransactionPage] = useState(1);
  const [transactionPageSize, setTransactionPageSize] = useState(5);
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
  const visibleInventory = useMemo(() => {
    const query = inventorySearch.trim().toLowerCase();
    return (inventoryQuery.data ?? []).filter((item) => {
      const variant = variantById.get(item.product_variant_id);
      const product = variant ? productById.get(variant.product_id) : undefined;
      const matchesSearch = !query || [product?.name, product?.sku, variant?.sku].some((value) => value?.toLowerCase().includes(query));
      return categoryMatches(product?.category, categoryFilter) && matchesSearch;
    }).sort((left, right) => {
      if (inventorySort === "stockAsc") return left.stock_quantity - right.stock_quantity;
      if (inventorySort === "reservedDesc") return right.reserved_quantity - left.reserved_quantity;
      if (inventorySort === "minimumDesc") return right.minimum_quantity - left.minimum_quantity;
      return right.stock_quantity - left.stock_quantity;
    });
  }, [inventoryQuery.data, variantById, productById, categoryFilter, inventorySearch, inventorySort]);
  const paginatedInventory = paginateItems(visibleInventory, inventoryPage, inventoryPageSize);
  const visibleTransactions = useMemo(() => (transactionsQuery.data ?? []).filter((transaction) => historyTypeFilter === "all" || transaction.transaction_type === historyTypeFilter), [transactionsQuery.data, historyTypeFilter]);
  const paginatedTransactions = paginateItems(visibleTransactions, transactionPage, transactionPageSize);

  useEffect(() => {
    setInventoryPage(1);
  }, [categoryFilter, lowStockOnly, inventorySearch, inventorySort]);
  useEffect(() => {
    setInventoryPage((page) => clampPage(page, inventoryPageSize, visibleInventory.length));
  }, [inventoryPageSize, visibleInventory.length]);
  useEffect(() => {
    setTransactionPage(1);
  }, [historyTypeFilter, inventoryId]);
  useEffect(() => {
    setTransactionPage((page) => clampPage(page, transactionPageSize, visibleTransactions.length));
  }, [transactionPageSize, visibleTransactions.length]);

  function submitTransaction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    transactionMutation.mutate();
  }

  return (
    <main className="min-h-screen min-w-0 overflow-x-hidden bg-[#F8F7FC] p-4 sm:p-6 text-slate-950">
      <div className="mx-auto grid min-w-0 max-w-7xl gap-6">
        <header className="min-w-0 max-w-full overflow-hidden rounded-2xl bg-white p-6 shadow-sm"><p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Sellora Inventory</p><h1 className="mt-2 text-3xl font-bold">{t("inventory.title")}</h1><p className="mt-1 text-slate-600">{t("inventory.subtitle")}</p></header>
        <FilterBar>
          <SearchInput value={inventorySearch} onChange={setInventorySearch} placeholder={t("inventory.searchPlaceholder")} />
          <label className="flex min-w-0 items-center gap-2 text-sm dark:text-slate-100"><input type="checkbox" checked={lowStockOnly} onChange={(event) => setLowStockOnly(event.target.checked)} /> {t("inventory.lowStockOnly")}</label>
          <select className="w-full min-w-0 max-w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm dark:border-white/10 dark:bg-white/10 dark:text-white" aria-label={t("inventory.filterByCategory")} value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value as CategoryFilter)}><option value="all">{t("inventory.allCategories")}</option>{categoryOptions.map((category) => <option key={category.value} value={category.value}>{category.label}</option>)}</select>
          <SortSelect value={inventorySort} onChange={setInventorySort} options={[{ value: "stockDesc", label: t("sort.stockDesc") }, { value: "stockAsc", label: t("sort.stockAsc") }, { value: "reservedDesc", label: t("sort.reservedDesc") }, { value: "minimumDesc", label: t("sort.minimumDesc") }]} />
          <select className="w-full min-w-0 max-w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm dark:border-white/10 dark:bg-white/10 dark:text-white" value={inventoryId} onChange={(event) => setInventoryId(event.target.value)}><option value="">{t("inventory.allHistory")}</option>{visibleInventory.map((item) => <option key={item.id} value={item.id}>{item.product_variant_id}</option>)}</select>
          <ResetFiltersButton onClick={() => { setInventorySearch(""); setLowStockOnly(false); setCategoryFilter("all"); setInventorySort("stockDesc"); }} />
        </FilterBar>
        <InventoryTable inventory={paginatedInventory} variants={variantsQuery.data ?? []} products={productsQuery.data ?? []} onEdit={canEdit ? setEditingInventory : undefined} />
        <PaginationControls page={inventoryPage} pageSize={inventoryPageSize} totalItems={visibleInventory.length} onPageChange={setInventoryPage} onPageSizeChange={(size) => { setInventoryPageSize(size); setInventoryPage(1); }} />
        <form className="grid min-w-0 max-w-full gap-3 overflow-hidden rounded-2xl bg-white p-4 shadow-sm md:grid-cols-5" onSubmit={submitTransaction}>
          <select className="w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" required value={inventoryId} onChange={(event) => setInventoryId(event.target.value)}><option value="">{t("inventory.selectInventory")}</option>{visibleInventory.map((item) => <option key={item.id} value={item.id}>{item.product_variant_id}</option>)}</select>
          <select className="w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" value={transactionType} onChange={(event) => setTransactionType(event.target.value as InventoryTransactionType)}>{TRANSACTION_TYPES.map((type) => <option key={type} value={type}>{t(`inventory.transactionTypes.${type}`)}</option>)}</select>
          <input className="w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" min={1} type="number" value={quantity} onChange={(event) => setQuantity(Number(event.target.value))} />
          <input className="w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" placeholder={t("inventory.reason")} value={reason} onChange={(event) => setReason(event.target.value)} />
          <button className="rounded-md bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60" disabled={!canEdit} type="submit">{t("inventory.adjustStock")}</button>
        </form>
        <section className="grid gap-3">
          <div className="grid min-w-0 gap-3 rounded-2xl bg-white p-4 shadow-sm dark:bg-[#15172A] md:grid-cols-[1fr_auto]">
            <select className="min-h-11 rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-white/10 dark:bg-white/10 dark:text-white" value={historyTypeFilter} onChange={(event) => setHistoryTypeFilter(event.target.value as InventoryTransactionType | "all")}>
              <option value="all">{t("inventory.allTransactionTypes")}</option>
              {TRANSACTION_TYPES.map((type) => <option key={type} value={type}>{t(`inventory.transactionTypes.${type}`)}</option>)}
            </select>
          </div>
          <InventoryTransactionHistory transactions={paginatedTransactions} />
          <PaginationControls page={transactionPage} pageSize={transactionPageSize} totalItems={visibleTransactions.length} onPageChange={setTransactionPage} onPageSizeChange={(size) => { setTransactionPageSize(size); setTransactionPage(1); }} />
        </section>
        {editingInventory ? <EditRecordDialog title={t("inventory.updateThresholds")} fields={[{ name: "incoming_quantity", label: t("inventory.incomingQuantity"), type: "number" }, { name: "minimum_quantity", label: t("inventory.minimumQuantity"), type: "number" }]} initialValues={editingInventory} isSubmitting={updateMutation.isPending} submitError={updateMutation.isError ? safeApiErrorMessage(updateMutation.error, "Unable to save inventory changes. Please try again.") : null} onClose={() => setEditingInventory(null)} onSubmit={(values) => updateMutation.mutate(values)} /> : null}
      </div>
    </main>
  );
}
// Localization regression compatibility marker: Adjust stock.
