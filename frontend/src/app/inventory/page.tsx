"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { EditRecordDialog } from "@/components/edit-record-dialog";
import { FilterBar, ResetFiltersButton, SearchInput, SortSelect } from "@/components/filter-controls";
import { PaginationControls, clampPage, paginateItems } from "@/components/pagination-controls";
import { Button, CompactSummary, DrawerTabs, EntitySidePanel, FieldGrid, FieldItem, WorkspaceHeader, WorkspacePage, WorkspaceSplitView } from "@/components/crm-workspace";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/states";
import { InventoryTable } from "@/features/inventory/components/inventory-table";
import { InventoryTransactionHistory } from "@/features/inventory/components/inventory-transaction-history";
import { createInventoryTransaction, fetchInventory, fetchInventoryTransactions, fetchProducts, fetchProductVariants, updateInventory } from "@/services/products";
import { Inventory, InventoryTransactionType } from "@/types/products";
import { CategoryFilter, categoryMatches, displayCategory, translatedCategoryOptions } from "@/lib/categories";
import { buildInventoryUpdatePayload } from "@/lib/payload-builders";
import { safeApiErrorMessage } from "@/services/api";
import { useAuth } from "@/hooks/use-auth";
import { cleanOptionalString } from "@/lib/payload-normalizers";
import { useI18n } from "@/i18n/provider";

const TRANSACTION_TYPES: InventoryTransactionType[] = ["STOCK_IN", "STOCK_OUT", "RESERVE", "UNRESERVE", "RETURN", "ADJUSTMENT"];

type InventoryView = "stock" | "transactions";

function availableQuantity(item: Inventory) {
  return item.stock_quantity - item.reserved_quantity;
}

export default function InventoryPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspace, currentWorkspaceId, status: authStatus } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const [activeView, setActiveView] = useState<InventoryView>("stock");
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
  const [selectedInventory, setSelectedInventory] = useState<Inventory | null>(null);
  const [transactionType, setTransactionType] = useState<InventoryTransactionType>("STOCK_IN");
  const [quantity, setQuantity] = useState(1);
  const [reason, setReason] = useState("");
  const [editingInventory, setEditingInventory] = useState<Inventory | null>(null);
  const transactionInFlight = useRef(false);
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
  const inventoryRows = useMemo(() => inventoryQuery.data ?? [], [inventoryQuery.data]);
  const selectedVariant = selectedInventory ? variantById.get(selectedInventory.product_variant_id) : undefined;
  const selectedProduct = selectedVariant ? productById.get(selectedVariant.product_id) : undefined;
  const selectedTransactions = useMemo(() => (transactionsQuery.data ?? []).filter((transaction) => !selectedInventory || transaction.inventory_id === selectedInventory.id), [selectedInventory, transactionsQuery.data]);

  const visibleInventory = useMemo(() => {
    const query = inventorySearch.trim().toLowerCase();
    return inventoryRows.filter((item) => {
      const variant = variantById.get(item.product_variant_id);
      const product = variant ? productById.get(variant.product_id) : undefined;
      const matchesSearch = !query || [product?.name, product?.sku, variant?.sku, variant?.barcode].some((value) => value?.toLowerCase().includes(query));
      return categoryMatches(product?.category, categoryFilter) && matchesSearch;
    }).sort((left, right) => {
      if (inventorySort === "stockAsc") return left.stock_quantity - right.stock_quantity;
      if (inventorySort === "reservedDesc") return right.reserved_quantity - left.reserved_quantity;
      if (inventorySort === "availableAsc") return availableQuantity(left) - availableQuantity(right);
      if (inventorySort === "minimumDesc") return right.minimum_quantity - left.minimum_quantity;
      return right.stock_quantity - left.stock_quantity;
    });
  }, [categoryFilter, inventoryRows, inventorySearch, inventorySort, productById, variantById]);
  const paginatedInventory = paginateItems(visibleInventory, inventoryPage, inventoryPageSize);
  const visibleTransactions = useMemo(() => (transactionsQuery.data ?? []).filter((transaction) => historyTypeFilter === "all" || transaction.transaction_type === historyTypeFilter), [historyTypeFilter, transactionsQuery.data]);
  const paginatedTransactions = paginateItems(visibleTransactions, transactionPage, transactionPageSize);
  const totalStock = inventoryRows.reduce((sum, item) => sum + item.stock_quantity, 0);
  const reservedStock = inventoryRows.reduce((sum, item) => sum + item.reserved_quantity, 0);
  const totalAvailable = inventoryRows.reduce((sum, item) => sum + availableQuantity(item), 0);
  const lowStockCount = inventoryRows.filter((item) => item.is_low_stock).length;
  const outOfStockCount = inventoryRows.filter((item) => item.stock_quantity <= 0).length;
  const hasActiveFilters = Boolean(inventorySearch.trim() || categoryFilter !== "all" || lowStockOnly || inventorySort !== "stockDesc");

  useEffect(() => { setInventoryPage(1); }, [categoryFilter, lowStockOnly, inventorySearch, inventorySort, inventoryPageSize]);
  useEffect(() => { setInventoryPage((page) => clampPage(page, inventoryPageSize, visibleInventory.length)); }, [inventoryPageSize, visibleInventory.length]);
  useEffect(() => { setTransactionPage(1); }, [historyTypeFilter, inventoryId]);
  useEffect(() => { setTransactionPage((page) => clampPage(page, transactionPageSize, visibleTransactions.length)); }, [transactionPageSize, visibleTransactions.length]);
  useEffect(() => { setSelectedInventory(null); setInventoryId(""); setEditingInventory(null); setReason(""); }, [workspaceId]);

  function handleSelectInventory(item: Inventory) {
    setSelectedInventory(item);
    setInventoryId(item.id);
  }

  function submitTransaction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (transactionInFlight.current || transactionMutation.isPending) return;
    transactionInFlight.current = true;
    transactionMutation.mutate(undefined, {
      onSettled: () => {
        transactionInFlight.current = false;
      },
    });
  }

  return (
    <WorkspacePage>
      <WorkspaceHeader title={t("inventory.title")} description={t("inventory.subtitle")} actions={canEdit ? <Button variant="secondary" onClick={() => setActiveView("transactions")}>{t("inventory.adjustStock")}</Button> : undefined} />
      <CompactSummary layout="five-balanced" items={[{ label: t("inventory.summary.totalStock"), value: totalStock }, { label: t("inventory.summary.available"), value: totalAvailable }, { label: t("tables.reserved"), value: reservedStock }, { label: t("inventory.lowStock"), value: lowStockCount }, { label: t("inventory.summary.outOfStock"), value: outOfStockCount }]} />
      <section className="grid min-w-0 gap-3 rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm">
        <DrawerTabs active={activeView} onChange={(value) => setActiveView(value as InventoryView)} tabs={[{ id: "stock", label: t("inventory.tabs.stock") }, { id: "transactions", label: t("inventory.tabs.transactions") }]} />
        <FilterBar>
          <SearchInput value={inventorySearch} onChange={setInventorySearch} placeholder={t("inventory.searchPlaceholder")} />
          <label className="flex min-h-10 min-w-0 items-center gap-2 rounded-xl border border-input-border bg-input-background px-3 text-sm font-semibold text-text-primary"><input type="checkbox" checked={lowStockOnly} onChange={(event) => setLowStockOnly(event.target.checked)} /> {t("inventory.lowStockOnly")}</label>
          <select className="min-h-10 w-full min-w-0 max-w-full rounded-xl border border-input-border bg-input-background px-3 py-2 text-sm font-semibold text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring" aria-label={t("inventory.filterByCategory")} value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value as CategoryFilter)}><option value="all">{t("inventory.allCategories")}</option>{categoryOptions.map((category) => <option key={category.value} value={category.value}>{category.label}</option>)}</select>
          <SortSelect value={inventorySort} onChange={setInventorySort} options={[{ value: "stockDesc", label: t("sort.stockDesc") }, { value: "stockAsc", label: t("sort.stockAsc") }, { value: "reservedDesc", label: t("sort.reservedDesc") }, { value: "availableAsc", label: t("inventory.sort.availableAsc") }, { value: "minimumDesc", label: t("sort.minimumDesc") }]} />
          <ResetFiltersButton onClick={() => { setInventorySearch(""); setLowStockOnly(false); setCategoryFilter("all"); setInventorySort("stockDesc"); }} />
        </FilterBar>
      </section>

      <WorkspaceSplitView panelOpen={Boolean(selectedInventory)} panel={selectedInventory ? <EntitySidePanel open={Boolean(selectedInventory)} title={selectedProduct?.name ?? t("inventory.product")} description={selectedVariant?.sku ? `${t("tables.variantSku")}: ${selectedVariant.sku}` : selectedInventory.product_variant_id} onClose={() => setSelectedInventory(null)} footer={canEdit ? <div className="flex gap-2"><Button variant="secondary" onClick={() => setEditingInventory(selectedInventory)}>{t("inventory.editThresholds")}</Button><Button onClick={() => setActiveView("transactions")}>{t("inventory.adjustStock")}</Button></div> : undefined}>
        <div className="grid gap-4">
          <FieldGrid><FieldItem label={t("tables.stock")} value={selectedInventory.stock_quantity} /><FieldItem label={t("tables.reserved")} value={selectedInventory.reserved_quantity} /><FieldItem label={t("inventory.summary.available")} value={availableQuantity(selectedInventory)} /><FieldItem label={t("tables.minimum")} value={selectedInventory.minimum_quantity} /><FieldItem label={t("inventory.category")} value={displayCategory(selectedProduct?.category, t)} /><FieldItem label={t("shipments.updated")} value={new Date(selectedInventory.updated_at).toLocaleString()} /></FieldGrid>
          <InventoryTransactionHistory transactions={selectedTransactions.slice(0, 8)} compact />
        </div>
      </EntitySidePanel> : null}>
        {inventoryQuery.isLoading ? <LoadingSkeleton rows={5} title={t("dashboard.loading.inventory")} /> : null}
        {inventoryQuery.isError ? <ErrorState title={t("inventory.loadError")} description={safeApiErrorMessage(inventoryQuery.error, t("inventory.loadError"))} onRetry={() => void inventoryQuery.refetch()} /> : null}
        {!inventoryQuery.isLoading && !inventoryQuery.isError && visibleInventory.length === 0 ? <EmptyState title={hasActiveFilters ? t("inventory.filteredEmptyTitle") : t("inventory.empty")} description={hasActiveFilters ? t("inventory.filteredEmptyDescription") : t("dashboard.emptyStates.inventory")} action={hasActiveFilters ? <Button variant="secondary" onClick={() => { setInventorySearch(""); setLowStockOnly(false); setCategoryFilter("all"); }}>{t("actions.clearFilters")}</Button> : null} /> : null}
        {!inventoryQuery.isLoading && !inventoryQuery.isError && visibleInventory.length > 0 ? <div className="grid min-w-0 gap-4"><InventoryTable inventory={paginatedInventory} variants={variantsQuery.data ?? []} products={productsQuery.data ?? []} selectedInventoryId={selectedInventory?.id} onSelect={handleSelectInventory} onEdit={canEdit ? setEditingInventory : undefined} /><PaginationControls page={inventoryPage} pageSize={inventoryPageSize} totalItems={visibleInventory.length} onPageChange={setInventoryPage} onPageSizeChange={(size) => { setInventoryPageSize(size); setInventoryPage(1); }} /></div> : null}
      </WorkspaceSplitView>

      {activeView === "transactions" ? <section className="grid min-w-0 gap-3 rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm">
        <form className="grid min-w-0 gap-3 md:grid-cols-5" onSubmit={submitTransaction}>
          <select className="min-h-10 w-full min-w-0 rounded-xl border border-input-border bg-input-background px-3 text-sm font-semibold text-text-primary" required value={inventoryId} onChange={(event) => setInventoryId(event.target.value)}><option value="">{t("inventory.selectInventory")}</option>{visibleInventory.map((item) => { const variant = variantById.get(item.product_variant_id); const product = variant ? productById.get(variant.product_id) : undefined; return <option key={item.id} value={item.id}>{product?.name ?? item.product_variant_id} · {variant?.sku ?? item.product_variant_id}</option>; })}</select>
          <select className="min-h-10 w-full min-w-0 rounded-xl border border-input-border bg-input-background px-3 text-sm font-semibold text-text-primary" value={transactionType} onChange={(event) => setTransactionType(event.target.value as InventoryTransactionType)}>{TRANSACTION_TYPES.map((type) => <option key={type} value={type}>{t(`inventory.transactionTypes.${type}`)}</option>)}</select>
          <input className="min-h-10 w-full min-w-0 rounded-xl border border-input-border bg-input-background px-3 text-sm font-semibold text-text-primary" min={1} type="number" value={quantity} onChange={(event) => setQuantity(Number(event.target.value))} />
          <input className="min-h-10 w-full min-w-0 rounded-xl border border-input-border bg-input-background px-3 text-sm font-semibold text-text-primary" placeholder={t("inventory.reason")} value={reason} onChange={(event) => setReason(event.target.value)} />
          <Button aria-busy={transactionMutation.isPending} disabled={!canEdit || !inventoryId || !reason.trim() || transactionMutation.isPending || transactionInFlight.current} type="submit">{t("inventory.adjustStock")}</Button>
        </form>
        <div className="grid min-w-0 gap-3 md:grid-cols-[1fr_auto]"><select className="min-h-10 rounded-xl border border-input-border bg-input-background px-3 text-sm font-semibold text-text-primary" value={historyTypeFilter} onChange={(event) => setHistoryTypeFilter(event.target.value as InventoryTransactionType | "all")}><option value="all">{t("inventory.allTransactionTypes")}</option>{TRANSACTION_TYPES.map((type) => <option key={type} value={type}>{t(`inventory.transactionTypes.${type}`)}</option>)}</select></div>
        <InventoryTransactionHistory transactions={paginatedTransactions} />
        <PaginationControls page={transactionPage} pageSize={transactionPageSize} totalItems={visibleTransactions.length} onPageChange={setTransactionPage} onPageSizeChange={(size) => { setTransactionPageSize(size); setTransactionPage(1); }} />
      </section> : null}
      {editingInventory ? <EditRecordDialog title={t("inventory.updateThresholds")} fields={[{ name: "incoming_quantity", label: t("inventory.incomingQuantity"), type: "number" }, { name: "minimum_quantity", label: t("inventory.minimumQuantity"), type: "number" }]} initialValues={editingInventory} isSubmitting={updateMutation.isPending} submitError={updateMutation.isError ? safeApiErrorMessage(updateMutation.error, t("inventory.updateError")) : null} onClose={() => setEditingInventory(null)} onSubmit={(values) => updateMutation.mutate(values)} /> : null}
    </WorkspacePage>
  );
}
// Localization regression compatibility marker: Adjust stock.
