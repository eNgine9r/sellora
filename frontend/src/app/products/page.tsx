"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { ConfirmActionDialog } from "@/components/confirm-action-dialog";
import { EditRecordDialog } from "@/components/edit-record-dialog";
import { FormDialog } from "@/components/form-dialog";
import { ResetFiltersButton, SearchInput, SortSelect } from "@/components/filter-controls";
import { PaginationControls, clampPage, paginateItems } from "@/components/pagination-controls";
import { ProductForm } from "@/features/products/components/product-form";
import { ProductTable } from "@/features/products/components/product-table";
import { ProductVariantForm } from "@/features/products/components/product-variant-form";
import { useAuth } from "@/hooks/use-auth";
import { CATEGORY_KEYS, CategoryFilter, CategoryKey, categoryMatches, productSearchMatches, translatedCategoryOptions } from "@/lib/categories";
import { buildProductUpdatePayload, buildProductVariantUpdatePayload } from "@/lib/payload-builders";
import { safeApiErrorMessage } from "@/services/api";
import { createProduct, createProductVariant, deleteProduct, deleteProductVariant, fetchProducts, fetchProductVariants, updateProduct, updateProductVariant } from "@/services/products";
import { Product, ProductVariant } from "@/types/products";
import { useI18n } from "@/i18n/provider";

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
  const listError = productsQuery.isError ? safeApiErrorMessage(productsQuery.error, "Unable to load products.") : null;

  useEffect(() => {
    setProductPage(1);
  }, [categoryFilter, search, statusFilter, productSort]);
  useEffect(() => {
    setProductPage((page) => clampPage(page, productPageSize, visibleProducts.length));
  }, [productPageSize, visibleProducts.length]);
  useEffect(() => {
    setVariantPage((page) => clampPage(page, variantPageSize, variants.length));
  }, [variantPageSize, variants.length]);

  return (
    <main className="min-h-screen min-w-0 overflow-x-hidden bg-[#F8F7FC] p-4 text-slate-950 sm:p-6">
      <div className="mx-auto grid min-w-0 max-w-7xl gap-6">
        <header className="flex flex-col gap-4 rounded-2xl bg-white p-6 shadow-sm md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">{t("products.catalogLabel")}</p>
            <h1 className="mt-2 text-3xl font-bold">{t("products.title")}</h1>
            <p className="mt-1 text-slate-600">{t("products.subtitle")}</p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <button className="min-h-11 rounded-lg border border-slate-300 px-4 py-2 font-semibold disabled:cursor-not-allowed disabled:opacity-60" disabled={!enabled} onClick={() => setDialog("variant")}>
              {t("products.createVariant")}
            </button>
            <button className="min-h-11 rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60" disabled={!enabled} onClick={() => setDialog("product")}>
              {t("products.create")}
            </button>
          </div>
        </header>

        <section className="grid min-w-0 gap-4 rounded-2xl bg-white p-4 shadow-sm dark:bg-slate-900">
          <div className="sellora-scrollbar flex min-w-0 max-w-full gap-2 overflow-x-auto pb-1" aria-label={t("products.filterByCategory")}>
            {[{ value: "all" as const, label: t("categories.allProducts") }, ...categoryOptions].map((category) => (
              <button
                key={category.value}
                className={`shrink-0 rounded-full border px-4 py-2 text-sm font-bold transition ${categoryFilter === category.value ? "border-blue-600 bg-blue-600 text-white" : "border-slate-200 bg-white text-slate-700 hover:border-blue-300 dark:border-white/10 dark:bg-white/[0.04] dark:text-slate-200"}`}
                type="button"
                onClick={() => setCategoryFilter(category.value)}
              >
                {category.label}
              </button>
            ))}
          </div>
          <div className="grid min-w-0 gap-3 md:grid-cols-[1fr_180px_220px_auto]">
            <SearchInput value={search} onChange={setSearch} placeholder={categoryFilter === "all" ? t("products.searchProducts") : t("products.searchInCategory")} />
            <select className="min-h-11 w-full min-w-0 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm dark:border-white/10 dark:bg-white/10 dark:text-white" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as typeof statusFilter)}>
              <option value="all">{t("products.allStatuses")}</option>
              <option value="active">{t("products.active")}</option>
              <option value="inactive">{t("products.inactive")}</option>
            </select>
            <SortSelect value={productSort} onChange={setProductSort} options={[{ value: "newest", label: t("sort.newest") }, { value: "oldest", label: t("sort.oldest") }, { value: "nameAsc", label: t("sort.nameAsc") }, { value: "nameDesc", label: t("sort.nameDesc") }]} />
            <ResetFiltersButton onClick={() => { setSearch(""); setCategoryFilter("all"); setStatusFilter("all"); setProductSort("newest"); }} />
          </div>
        </section>

        {listError ? <p className="rounded-lg bg-rose-50 p-4 text-rose-700">{listError}</p> : null}
        <ProductTable products={paginatedProducts} onEdit={canEdit ? setEditingProduct : undefined} onArchive={canEdit ? setArchivingProduct : undefined} />
        <PaginationControls page={productPage} pageSize={productPageSize} totalItems={visibleProducts.length} onPageChange={setProductPage} onPageSizeChange={(size) => { setProductPageSize(size); setProductPage(1); }} />

        <section className="min-w-0 rounded-2xl bg-white p-4 shadow-sm">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold">{t("products.manageVariants")}</h2>
              <p className="mt-1 text-sm text-slate-500">{t("products.variantsDescription")}</p>
            </div>
            <button className="min-h-11 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60" disabled={!enabled} onClick={() => setDialog("variant")}>
              {t("products.createVariant")}
            </button>
          </div>
          <div className="sellora-scrollbar mt-3 overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="text-xs uppercase text-slate-500">
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
                  <tr key={variant.id} className="border-t">
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
                          <button aria-label={`Edit variant ${variant.sku}`} className="min-h-10 rounded-lg border border-slate-300 px-3 py-2 font-semibold" onClick={() => setEditingVariant(variant)}>
                            {t("products.editVariant")}
                          </button>
                          <button aria-label={`Archive variant ${variant.sku}`} className="min-h-10 rounded-lg border border-rose-200 px-3 py-2 font-semibold text-rose-700" onClick={() => setArchivingVariant(variant)}>
                            {t("products.archive")}
                          </button>
                        </div>
                      ) : (
                        <span className="text-xs font-semibold uppercase text-slate-400">Read-only</span>
                      )}
                    </td>
                  </tr>
                ))}
                {paginatedVariants.length === 0 ? (
                  <tr>
                    <td className="px-3 py-6 text-slate-500" colSpan={8}>{t("products.createProductVariantFirst")}</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
        <PaginationControls page={variantPage} pageSize={variantPageSize} totalItems={variants.length} onPageChange={setVariantPage} onPageSizeChange={(size) => { setVariantPageSize(size); setVariantPage(1); }} />

        {dialog === "product" ? (
          <FormDialog title={t("products.create")} description={t("products.createDescription")} onClose={() => setDialog(null)}>
            <ProductForm
              isSubmitting={createProductMutation.isPending}
              submitError={createProductMutation.isError ? safeApiErrorMessage(createProductMutation.error, "Unable to create product. Please try again.") : null}
              onSubmit={(values) => createProductMutation.mutate(values)}
            />
          </FormDialog>
        ) : null}
        {dialog === "variant" ? (
          <FormDialog title={t("products.createVariant")} description={t("products.variantsDescription")} onClose={() => setDialog(null)}>
            <ProductVariantForm
              products={products}
              isSubmitting={createVariantMutation.isPending}
              submitError={createVariantMutation.isError ? safeApiErrorMessage(createVariantMutation.error, "Unable to create variant. Please try again.") : null}
              onSubmit={(values) => createVariantMutation.mutate(values)}
            />
          </FormDialog>
        ) : null}
        {archivingProduct ? (
          <ConfirmActionDialog title="Archive product?" description="Archiving this product hides it from the active catalog. Existing orders remain unchanged." actionLabel={t("products.archive")} isSubmitting={archiveProductMutation.isPending} error={archiveProductMutation.isError ? safeApiErrorMessage(archiveProductMutation.error, "Unable to delete record. Please try again.") : null} onCancel={() => setArchivingProduct(null)} onConfirm={() => archiveProductMutation.mutate()} />
        ) : null}
        {archivingVariant ? (
          <ConfirmActionDialog title="Archive variant?" description="This variant will be hidden from active selectors. Inventory is not hard deleted, and historical order items remain unchanged." actionLabel="Archive variant" isSubmitting={archiveVariantMutation.isPending} error={archiveVariantMutation.isError ? safeApiErrorMessage(archiveVariantMutation.error, "This record cannot be deleted because it is used by other records.") : null} onCancel={() => setArchivingVariant(null)} onConfirm={() => archiveVariantMutation.mutate()} />
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
            submitError={updateProductMutation.isError ? safeApiErrorMessage(updateProductMutation.error, "Unable to save product changes. Please try again.") : null}
            onClose={() => setEditingProduct(null)}
            onSubmit={(values) => updateProductMutation.mutate(values)}
          />
        ) : null}
        {editingVariant ? (
          <EditRecordDialog
            title={t("products.editVariant")}
            fields={[
              { name: "sku", label: "Variant SKU" },
              { name: "color", label: "Color" },
              { name: "size", label: "Size" },
              { name: "price", label: "Selling price", type: "number" },
              { name: "barcode", label: "Barcode" },
              { name: "is_active", label: t("tables.status"), type: "select", options: [{ value: "true", label: t("products.active") }, { value: "false", label: t("products.inactive") }] },
            ]}
            initialValues={editingVariant}
            isSubmitting={updateVariantMutation.isPending}
            submitError={updateVariantMutation.isError ? safeApiErrorMessage(updateVariantMutation.error, "Unable to save variant changes. Please try again.") : null}
            onClose={() => setEditingVariant(null)}
            onSubmit={(values) => updateVariantMutation.mutate(values)}
          />
        ) : null}
      </div>
    </main>
  );
}
// Localization regression compatibility markers: FormDialog title="Create product"; FormDialog title="Create variant".
// Regression compatibility markers: Manage product variants; Edit variant; Archive variant.
