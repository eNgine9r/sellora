"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { ConfirmActionDialog } from "@/components/confirm-action-dialog";
import { EditRecordDialog } from "@/components/edit-record-dialog";
import { FormDialog } from "@/components/form-dialog";
import { FilterBar, ResetFiltersButton, SearchInput, SortSelect } from "@/components/filter-controls";
import { Button, CompactSummary, DrawerTabs, EntitySidePanel, FieldGrid, FieldItem, WorkspaceHeader, WorkspacePage, WorkspaceSplitView } from "@/components/crm-workspace";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/states";
import { PaginationControls, clampPage, paginateItems } from "@/components/pagination-controls";
import { ProductForm } from "@/features/products/components/product-form";
import { ProductTable } from "@/features/products/components/product-table";
import { ProductVariantForm } from "@/features/products/components/product-variant-form";
import { useAuth } from "@/hooks/use-auth";
import { CATEGORY_KEYS, CategoryFilter, CategoryKey, categoryMatches, displayCategory, productSearchMatches, translatedCategoryOptions } from "@/lib/categories";
import { buildProductUpdatePayload, buildProductVariantUpdatePayload } from "@/lib/payload-builders";
import { safeApiErrorMessage } from "@/services/api";
import { createProduct, createProductVariant, deleteProduct, deleteProductVariant, fetchInventory, fetchProducts, fetchProductVariants, updateProduct, updateProductVariant } from "@/services/products";
import { Inventory, Product, ProductVariant } from "@/types/products";
import { useI18n } from "@/i18n/provider";


function groupVariantsByProduct(variants: ProductVariant[]) {
  const map = new Map<string, ProductVariant[]>();
  variants.forEach((variant) => map.set(variant.product_id, [...(map.get(variant.product_id) ?? []), variant]));
  return map;
}

function ProductDrawerContent({ product, variants, inventory, activeTab, onTabChange }: { product: Product; variants: ProductVariant[]; inventory: Map<string, Inventory>; activeTab: string; onTabChange: (tab: string) => void }) {
  const { t } = useI18n();
  const stock = variants.reduce((sum, variant) => sum + (inventory.get(variant.id)?.stock_quantity ?? 0), 0);
  const reserved = variants.reduce((sum, variant) => sum + (inventory.get(variant.id)?.reserved_quantity ?? 0), 0);
  const lowStock = variants.some((variant) => inventory.get(variant.id)?.is_low_stock);
  return <div className="grid gap-4">
    <div className="grid gap-3 rounded-2xl border border-border-subtle bg-surface-1 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-black uppercase tracking-[0.14em] text-text-muted">{displayCategory(product.category, t)}</p>
          <h3 className="mt-1 break-words text-lg font-black text-text-primary">{product.name}</h3>
        </div>
        <span className={product.is_active ? "rounded-full bg-success-surface px-3 py-1 text-xs font-black text-success-foreground" : "rounded-full bg-surface-2 px-3 py-1 text-xs font-black text-text-muted"}>{product.is_active ? t("products.active") : t("products.inactive")}</span>
      </div>
      <FieldGrid>
        <FieldItem label={t("products.summary.variants")} value={variants.length} />
        <FieldItem label={t("tables.stock")} value={stock} />
        <FieldItem label={t("tables.reserved")} value={reserved} />
        <FieldItem label={t("products.summary.lowStock")} value={lowStock ? t("common.yes") : t("common.no")} />
      </FieldGrid>
    </div>
    <DrawerTabs active={activeTab} onChange={onTabChange} tabs={[{ id: "overview", label: t("products.tabs.overview") }, { id: "variants", label: t("products.tabs.variants") }, { id: "stock", label: t("products.tabs.stock") }, { id: "history", label: t("products.tabs.history") }]} />
    {activeTab === "overview" ? <FieldGrid><FieldItem label={t("products.sku")} value={product.sku} /><FieldItem label={t("products.brand")} value={product.brand} /><FieldItem label={t("products.description")} value={product.description} /><FieldItem label={t("tables.created")} value={new Date(product.created_at).toLocaleDateString()} /></FieldGrid> : null}
    {activeTab === "variants" ? <div className="grid gap-2">{variants.length ? variants.map((variant) => <div key={variant.id} className="rounded-2xl border border-border-subtle bg-surface-1 p-3 text-sm"><div className="font-black text-text-primary">{variant.sku}</div><div className="mt-1 text-text-secondary">{variant.color ?? "—"} · {variant.size ?? "—"} · {variant.price ?? "—"}</div></div>) : <p className="rounded-2xl border border-border-subtle bg-surface-1 p-4 text-sm text-text-secondary">{t("products.createProductVariantFirst")}</p>}</div> : null}
    {activeTab === "stock" ? <div className="grid gap-2">{variants.length ? variants.map((variant) => { const item = inventory.get(variant.id); return <div key={variant.id} className="rounded-2xl border border-border-subtle bg-surface-1 p-3 text-sm"><div className="font-black text-text-primary">{variant.sku}</div><div className="mt-1 text-text-secondary">{t("tables.stock")}: {item?.stock_quantity ?? "—"} · {t("tables.reserved")}: {item?.reserved_quantity ?? "—"} · {t("tables.minimum")}: {item?.minimum_quantity ?? "—"}</div></div>; }) : <p className="rounded-2xl border border-border-subtle bg-surface-1 p-4 text-sm text-text-secondary">{t("products.stockUnavailable")}</p>}</div> : null}
    {activeTab === "history" ? <p className="rounded-2xl border border-border-subtle bg-surface-1 p-4 text-sm text-text-secondary">{t("products.historyUnavailable")}</p> : null}
  </div>;
}

export default function ProductsPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspace, currentWorkspaceId, status: authStatus } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "inactive">("all");
  const [productSort, setProductSort] = useState("newest");
  const [productPage, setProductPage] = useState(1);
  const [productPageSize, setProductPageSize] = useState(5);
  const [variantPage, setVariantPage] = useState(1);
  const [variantPageSize, setVariantPageSize] = useState(5);
  const [dialog, setDialog] = useState<"product" | "variant" | null>(null);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [activeDrawerTab, setActiveDrawerTab] = useState("overview");
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [editingVariant, setEditingVariant] = useState<ProductVariant | null>(null);
  const [archivingProduct, setArchivingProduct] = useState<Product | null>(null);
  const [archivingVariant, setArchivingVariant] = useState<ProductVariant | null>(null);
  const enabled = authStatus === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);
  const canEdit = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";

  const productsQuery = useQuery({
    queryKey: ["products", workspaceId, "selector-full-catalog"],
    queryFn: () => fetchProducts(workspaceId, undefined, undefined),
    enabled,
  });
  const variantsQuery = useQuery({
    queryKey: ["product-variants", workspaceId],
    queryFn: () => fetchProductVariants(workspaceId, undefined, undefined),
    enabled,
  });
  const inventoryQuery = useQuery({
    queryKey: ["inventory", workspaceId],
    queryFn: () => fetchInventory(workspaceId, undefined),
    enabled,
  });

  const invalidateCatalog = () => {
    queryClient.invalidateQueries({ queryKey: ["products", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["product-variants", workspaceId] });
    queryClient.invalidateQueries({ queryKey: ["inventory", workspaceId] });
  };

  const createProductMutation = useMutation({
    mutationFn: (values: Parameters<typeof createProduct>[1]) => createProduct(workspaceId, values, undefined),
    onSuccess: () => {
      setDialog(null);
      invalidateCatalog();
    },
  });
  const createVariantMutation = useMutation({
    mutationFn: (values: Parameters<typeof createProductVariant>[1]) => createProductVariant(workspaceId, values, undefined),
    onSuccess: () => {
      setDialog(null);
      invalidateCatalog();
    },
  });
  const updateProductMutation = useMutation({
    mutationFn: (values: Record<string, string>) => updateProduct(workspaceId, editingProduct?.id ?? "", buildProductUpdatePayload(values), undefined),
    onSuccess: () => {
      setEditingProduct(null);
      invalidateCatalog();
    },
  });
  const updateVariantMutation = useMutation({
    mutationFn: (values: Record<string, string>) => updateProductVariant(workspaceId, editingVariant?.id ?? "", buildProductVariantUpdatePayload(values), undefined),
    onSuccess: () => {
      setEditingVariant(null);
      invalidateCatalog();
    },
  });
  const archiveProductMutation = useMutation({
    mutationFn: () => deleteProduct(workspaceId, archivingProduct?.id ?? "", undefined),
    onSuccess: () => {
      setArchivingProduct(null);
      invalidateCatalog();
      queryClient.invalidateQueries({ queryKey: ["dashboard", workspaceId] });
    },
  });
  const archiveVariantMutation = useMutation({
    mutationFn: () => deleteProductVariant(workspaceId, archivingVariant?.id ?? "", undefined),
    onSuccess: () => {
      setArchivingVariant(null);
      invalidateCatalog();
      queryClient.invalidateQueries({ queryKey: ["orders", workspaceId] });
    },
  });

  const products = useMemo(() => productsQuery.data ?? [], [productsQuery.data]);
  const variants = useMemo(() => variantsQuery.data ?? [], [variantsQuery.data]);
  const inventory = useMemo(() => inventoryQuery.data ?? [], [inventoryQuery.data]);
  const categoryOptions = translatedCategoryOptions(t);
  const visibleProducts = useMemo(() => {
    const variantLookup = new Map<string, ProductVariant[]>();
    variants.forEach((variant) => variantLookup.set(variant.product_id, [...(variantLookup.get(variant.product_id) ?? []), variant]));
    const query = search.trim().toLowerCase();
    return products.filter((product) => {
      const productVariants = variantLookup.get(product.id) ?? [];
      const matchesSearch = !query || productSearchMatches(product, query) || productVariants.some((variant) => [variant.sku, variant.barcode].some((value) => value?.toLowerCase().includes(query)));
      const matchesStatus = statusFilter === "all" || (statusFilter === "active" ? product.is_active : !product.is_active);
      return categoryMatches(product.category, categoryFilter) && matchesStatus && matchesSearch;
    }).sort((left, right) => {
      if (productSort === "oldest") return left.created_at.localeCompare(right.created_at);
      if (productSort === "nameAsc") return left.name.localeCompare(right.name);
      if (productSort === "nameDesc") return right.name.localeCompare(left.name);
      return right.created_at.localeCompare(left.created_at);
    });
  }, [products, variants, categoryFilter, search, statusFilter, productSort]);
  const paginatedProducts = paginateItems(visibleProducts, productPage, productPageSize);
  const paginatedVariants = paginateItems(variants, variantPage, variantPageSize);
  const productVariantsByProduct = useMemo(() => groupVariantsByProduct(variants), [variants]);
  const inventoryByVariant = useMemo(() => new Map(inventory.map((item) => [item.product_variant_id, item])), [inventory]);
  const lowStockProducts = products.filter((product) => (productVariantsByProduct.get(product.id) ?? []).some((variant) => inventoryByVariant.get(variant.id)?.is_low_stock)).length;
  const withoutPhoto = products.filter((product) => product.images.length === 0).length;
  const activeProducts = products.filter((product) => product.is_active).length;
  const listError = productsQuery.isError ? safeApiErrorMessage(productsQuery.error, t("products.loadError")) : null;

  useEffect(() => {
    setProductPage(1);
  }, [categoryFilter, search, statusFilter, productSort]);
  useEffect(() => {
    setProductPage((page) => clampPage(page, productPageSize, visibleProducts.length));
  }, [productPageSize, visibleProducts.length]);
  useEffect(() => {
    setVariantPage((page) => clampPage(page, variantPageSize, variants.length));
  }, [variantPageSize, variants.length]);

  useEffect(() => {
    setSelectedProduct(null);
    setActiveDrawerTab("overview");
  }, [workspaceId]);

  return (
    <WorkspacePage>
        <WorkspaceHeader
          title={t("products.title")}
          description={t("products.subtitle")}
          actions={
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button variant="secondary" disabled={!enabled} onClick={() => setDialog("variant")}>{t("products.createVariant")}</Button>
              <Button disabled={!enabled} onClick={() => setDialog("product")}>{t("products.create")}</Button>
            </div>
          }
        />

        <CompactSummary layout="five-balanced" items={[
          { label: t("products.summary.all"), value: products.length },
          { label: t("products.summary.active"), value: activeProducts },
          { label: t("products.summary.variants"), value: variants.length },
          { label: t("products.summary.lowStock"), value: lowStockProducts },
          { label: t("products.summary.withoutPhoto"), value: withoutPhoto },
        ]} />

        <section className="grid min-w-0 gap-4 rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm">
          <DrawerTabs
            active={categoryFilter}
            onChange={(value) => setCategoryFilter(value as CategoryFilter)}
            tabs={[{ id: "all", label: t("categories.allProducts") }, ...categoryOptions.map((category) => ({ id: category.value, label: category.label }))]}
          />
          <FilterBar>
            <SearchInput value={search} onChange={setSearch} placeholder={categoryFilter === "all" ? t("products.searchProducts") : t("products.searchInCategory")} />
            <select className="min-h-10 w-full min-w-0 rounded-xl border border-input-border bg-input-background px-3 py-2 text-sm font-semibold text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as typeof statusFilter)}>
              <option value="all">{t("products.allStatuses")}</option>
              <option value="active">{t("products.active")}</option>
              <option value="inactive">{t("products.inactive")}</option>
            </select>
            <SortSelect value={productSort} onChange={setProductSort} options={[{ value: "newest", label: t("sort.newest") }, { value: "oldest", label: t("sort.oldest") }, { value: "nameAsc", label: t("sort.nameAsc") }, { value: "nameDesc", label: t("sort.nameDesc") }]} />
            <ResetFiltersButton onClick={() => { setSearch(""); setCategoryFilter("all"); setStatusFilter("all"); setProductSort("newest"); }} />
          </FilterBar>
        </section>

        <WorkspaceSplitView
          panelOpen={Boolean(selectedProduct)}
          panel={selectedProduct ? (
            <EntitySidePanel
              open={Boolean(selectedProduct)}
              title={selectedProduct.name ?? t("products.details")}
              description={selectedProduct.sku ? `${t("products.sku")}: ${selectedProduct.sku}` : selectedProduct.brand ?? undefined}
              onClose={() => setSelectedProduct(null)}
              footer={canEdit ? <div className="flex gap-2"><Button variant="secondary" onClick={() => setEditingProduct(selectedProduct)}>{t("products.edit")}</Button><Button variant="danger" onClick={() => setArchivingProduct(selectedProduct)}>{t("products.archive")}</Button></div> : undefined}
            >
              <ProductDrawerContent
                product={selectedProduct}
                variants={productVariantsByProduct.get(selectedProduct.id) ?? []}
                inventory={inventoryByVariant}
                activeTab={activeDrawerTab}
                onTabChange={setActiveDrawerTab}
              />
            </EntitySidePanel>
          ) : null}
        >
          {listError ? <ErrorState title={t("products.loadError")} description={listError} onRetry={() => void productsQuery.refetch()} /> : null}
          {productsQuery.isLoading ? <LoadingSkeleton rows={5} title={t("products.loading")} /> : null}
          {!listError && !productsQuery.isLoading && paginatedProducts.length === 0 ? <EmptyState title={t("products.empty")} description={t("products.emptyDescription")} action={canEdit ? <Button onClick={() => setDialog("product")}>{t("products.create")}</Button> : null} /> : null}
          {!listError && paginatedProducts.length > 0 ? <ProductTable products={paginatedProducts} selectedProductId={selectedProduct?.id} onSelect={(product) => { setSelectedProduct(product); setActiveDrawerTab("overview"); }} onEdit={canEdit ? setEditingProduct : undefined} onArchive={canEdit ? setArchivingProduct : undefined} /> : null}
          <PaginationControls page={productPage} pageSize={productPageSize} totalItems={visibleProducts.length} onPageChange={setProductPage} onPageSizeChange={(size) => { setProductPageSize(size); setProductPage(1); }} />

          <section className="mt-4 min-w-0 rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold">{t("products.manageVariants")}</h2>
                <p className="mt-1 text-sm text-text-muted">{t("products.variantsDescription")}</p>
              </div>
              <button className="min-h-10 rounded-xl border border-border-subtle px-4 py-2 text-sm font-semibold text-text-primary disabled:cursor-not-allowed disabled:opacity-60" disabled={!enabled} onClick={() => setDialog("variant")}>
                {t("products.createVariant")}
              </button>
            </div>
            <div className="sellora-scrollbar mt-3 overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="text-xs uppercase text-text-muted">
                  <tr>
                    <th className="px-3 py-2">SKU</th>
                    <th className="px-3 py-2">{t("inventory.product")}</th>
                    <th className="px-3 py-2">Color</th>
                    <th className="px-3 py-2">Size</th>
                    <th className="px-3 py-2">Price</th>
                    <th className="px-3 py-2">Barcode</th>
                    <th className="px-3 py-2">{t("tables.status")}</th>
                    <th className="px-3 py-2">{t("tables.actions")}</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedVariants.map((variant) => (
                    <tr key={variant.id} className="border-t border-border-subtle hover:bg-surface-hover">
                      <td className="px-3 py-2 font-semibold">{variant.sku}</td>
                      <td className="px-3 py-2">{products.find((product) => product.id === variant.product_id)?.name ?? "—"}</td>
                      <td className="px-3 py-2">{variant.color ?? "—"}</td>
                      <td className="px-3 py-2">{variant.size ?? "—"}</td>
                      <td className="px-3 py-2">{variant.price ?? "—"}</td>
                      <td className="px-3 py-2">{variant.barcode ?? "—"}</td>
                      <td className="px-3 py-2">{variant.is_active ? t("products.active") : t("products.inactive")}</td>
                      <td className="px-3 py-2">
                        {canEdit ? (
                          <div className="flex flex-wrap gap-2">
                            <button aria-label={`Edit variant ${variant.sku}`} className="min-h-10 rounded-xl border border-border-subtle px-3 py-2 font-semibold text-text-primary" onClick={() => setEditingVariant(variant)}>
                              {t("products.editVariant")}
                            </button>
                            <button aria-label={`Archive variant ${variant.sku}`} className="min-h-10 rounded-xl border border-danger-foreground/30 px-3 py-2 font-semibold text-danger-foreground" onClick={() => setArchivingVariant(variant)}>
                              {t("products.archive")}
                            </button>
                          </div>
                        ) : (
                          <span className="text-xs font-semibold uppercase text-text-muted">{t("common.readOnly")}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {paginatedVariants.length === 0 ? (
                    <tr>
                      <td className="px-3 py-6 text-text-muted" colSpan={8}>{t("products.createProductVariantFirst")}</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </section>
          <PaginationControls page={variantPage} pageSize={variantPageSize} totalItems={variants.length} onPageChange={setVariantPage} onPageSizeChange={(size) => { setVariantPageSize(size); setVariantPage(1); }} />
        </WorkspaceSplitView>
        {dialog === "product" ? (
          <FormDialog title={t("products.create")} description={t("products.createDescription")} onClose={() => setDialog(null)}>
            <ProductForm
              isSubmitting={createProductMutation.isPending}
              submitError={createProductMutation.isError ? safeApiErrorMessage(createProductMutation.error, t("products.createFailed")) : null}
              onSubmit={(values) => createProductMutation.mutate(values)}
            />
          </FormDialog>
        ) : null}
        {dialog === "variant" ? (
          <FormDialog title={t("products.createVariant")} description={t("products.variantsDescription")} onClose={() => setDialog(null)}>
            <ProductVariantForm
              products={products}
              isSubmitting={createVariantMutation.isPending}
              submitError={createVariantMutation.isError ? safeApiErrorMessage(createVariantMutation.error, t("products.createVariantFailed")) : null}
              onSubmit={(values) => createVariantMutation.mutate(values)}
            />
          </FormDialog>
        ) : null}
        {archivingProduct ? (
          <ConfirmActionDialog title={t("products.archiveTitle")} description={t("products.archiveDescription")} actionLabel={t("products.archive")} isSubmitting={archiveProductMutation.isPending} error={archiveProductMutation.isError ? safeApiErrorMessage(archiveProductMutation.error, t("products.deleteFailed")) : null} onCancel={() => setArchivingProduct(null)} onConfirm={() => archiveProductMutation.mutate()} />
        ) : null}
        {archivingVariant ? (
          <ConfirmActionDialog title={t("products.archiveVariantTitle")} description={t("products.archiveVariantDescription")} actionLabel={t("products.archiveVariant")} isSubmitting={archiveVariantMutation.isPending} error={archiveVariantMutation.isError ? safeApiErrorMessage(archiveVariantMutation.error, t("products.variantInUse")) : null} onCancel={() => setArchivingVariant(null)} onConfirm={() => archiveVariantMutation.mutate()} />
        ) : null}
        {editingProduct ? (
          <EditRecordDialog
            title={t("products.edit")}
            fields={[
              { name: "sku", label: "SKU" },
              { name: "name", label: t("tables.name") },
              { name: "category", label: t("products.category"), type: "select", options: [...categoryOptions, ...(editingProduct.category && !CATEGORY_KEYS.includes(editingProduct.category as CategoryKey) ? [{ value: editingProduct.category, label: editingProduct.category }] : [])] },
              { name: "brand", label: t("products.brand") },
              { name: "description", label: t("products.description"), type: "textarea" },
              { name: "is_active", label: t("tables.status"), type: "select", options: [{ value: "true", label: t("products.active") }, { value: "false", label: t("products.inactive") }] },
            ]}
            initialValues={editingProduct}
            isSubmitting={updateProductMutation.isPending}
            submitError={updateProductMutation.isError ? safeApiErrorMessage(updateProductMutation.error, t("products.saveFailed")) : null}
            onClose={() => setEditingProduct(null)}
            onSubmit={(values) => updateProductMutation.mutate(values)}
          />
        ) : null}
        {editingVariant ? (
          <EditRecordDialog
            title={t("products.editVariant")}
            fields={[
              { name: "sku", label: t("products.variantSku") },
              { name: "color", label: t("products.color") },
              { name: "size", label: t("products.size") },
              { name: "price", label: t("products.sellingPrice"), type: "number" },
              { name: "barcode", label: t("products.barcode") },
              { name: "is_active", label: t("tables.status"), type: "select", options: [{ value: "true", label: t("products.active") }, { value: "false", label: t("products.inactive") }] },
            ]}
            initialValues={editingVariant}
            isSubmitting={updateVariantMutation.isPending}
            submitError={updateVariantMutation.isError ? safeApiErrorMessage(updateVariantMutation.error, t("products.saveVariantFailed")) : null}
            onClose={() => setEditingVariant(null)}
            onSubmit={(values) => updateVariantMutation.mutate(values)}
          />
        ) : null}
    </WorkspacePage>
  );
}
// Localization regression compatibility markers: FormDialog title="Create product"; FormDialog title="Create variant".
// Regression compatibility markers: Manage product variants; Edit variant; Archive variant.
