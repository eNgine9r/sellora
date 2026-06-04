"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ConfirmActionDialog } from "@/components/confirm-action-dialog";
import { EditRecordDialog } from "@/components/edit-record-dialog";
import { ProductForm } from "@/features/products/components/product-form";
import { ProductTable } from "@/features/products/components/product-table";
import { ProductVariantForm } from "@/features/products/components/product-variant-form";
import { useAuth } from "@/hooks/use-auth";
import { buildProductUpdatePayload, buildProductVariantUpdatePayload } from "@/lib/payload-builders";
import { safeApiErrorMessage } from "@/services/api";
import { createProduct, createProductVariant, deleteProduct, deleteProductVariant, fetchProducts, fetchProductVariants, updateProduct, updateProductVariant } from "@/services/products";
import { Product, ProductVariant } from "@/types/products";

export default function ProductsPage() {
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspace, currentWorkspaceId, status: authStatus } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const [search, setSearch] = useState("");
  const [dialog, setDialog] = useState<"product" | "variant" | null>(null);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [editingVariant, setEditingVariant] = useState<ProductVariant | null>(null);
  const [archivingProduct, setArchivingProduct] = useState<Product | null>(null);
  const [archivingVariant, setArchivingVariant] = useState<ProductVariant | null>(null);
  const enabled = authStatus === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);
  const canEdit = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";

  const productsQuery = useQuery({
    queryKey: ["products", workspaceId, search],
    queryFn: () => fetchProducts(workspaceId, search.trim() || undefined, undefined),
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

  const products = productsQuery.data ?? [];
  const variants = variantsQuery.data ?? [];
  const listError = productsQuery.isError ? safeApiErrorMessage(productsQuery.error, "Unable to load products.") : null;

  return (
    <main className="min-h-screen bg-[#F8F7FC] p-4 text-slate-950 sm:p-6">
      <div className="mx-auto grid max-w-7xl gap-6">
        <header className="flex flex-col gap-4 rounded-2xl bg-white p-6 shadow-sm md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Sellora Catalog</p>
            <h1 className="mt-2 text-3xl font-bold">Products</h1>
            <p className="mt-1 text-slate-600">Manage product images, product SKUs, variants, and variant SKUs.</p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <button className="min-h-11 rounded-lg border border-slate-300 px-4 py-2 font-semibold disabled:cursor-not-allowed disabled:opacity-60" disabled={!enabled} onClick={() => setDialog("variant")}>
              Create variant
            </button>
            <button className="min-h-11 rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60" disabled={!enabled} onClick={() => setDialog("product")}>
              Create product
            </button>
          </div>
        </header>

        <section className="grid gap-3 rounded-2xl bg-white p-4 shadow-sm md:grid-cols-3">
          <input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Search products" value={search} onChange={(event) => setSearch(event.target.value)} />
        </section>

        {listError ? <p className="rounded-lg bg-rose-50 p-4 text-rose-700">{listError}</p> : null}
        <ProductTable products={products} onEdit={canEdit ? setEditingProduct : undefined} onArchive={canEdit ? setArchivingProduct : undefined} />

        <section className="rounded-2xl bg-white p-4 shadow-sm">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold">Manage product variants</h2>
              <p className="mt-1 text-sm text-slate-500">Use each row action to edit variant SKU, color, size, price, barcode, and status.</p>
            </div>
            <button className="min-h-11 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60" disabled={!enabled} onClick={() => setDialog("variant")}>
              Add variant
            </button>
          </div>
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">SKU</th>
                  <th className="px-3 py-2">Product</th>
                  <th className="px-3 py-2">Color</th>
                  <th className="px-3 py-2">Size</th>
                  <th className="px-3 py-2">Price</th>
                  <th className="px-3 py-2">Barcode</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {variants.map((variant) => (
                  <tr key={variant.id} className="border-t">
                    <td className="px-3 py-2 font-semibold">{variant.sku}</td>
                    <td className="px-3 py-2">{products.find((product) => product.id === variant.product_id)?.name ?? "—"}</td>
                    <td className="px-3 py-2">{variant.color ?? "—"}</td>
                    <td className="px-3 py-2">{variant.size ?? "—"}</td>
                    <td className="px-3 py-2">{variant.price ?? "—"}</td>
                    <td className="px-3 py-2">{variant.barcode ?? "—"}</td>
                    <td className="px-3 py-2">{variant.is_active ? "Active" : "Inactive"}</td>
                    <td className="px-3 py-2">
                      {canEdit ? (
                        <div className="flex flex-wrap gap-2">
                          <button aria-label={`Edit variant ${variant.sku}`} className="min-h-10 rounded-lg border border-slate-300 px-3 py-2 font-semibold" onClick={() => setEditingVariant(variant)}>
                            Edit variant
                          </button>
                          <button aria-label={`Archive variant ${variant.sku}`} className="min-h-10 rounded-lg border border-rose-200 px-3 py-2 font-semibold text-rose-700" onClick={() => setArchivingVariant(variant)}>
                            Archive variant
                          </button>
                        </div>
                      ) : (
                        <span className="text-xs font-semibold uppercase text-slate-400">Read-only</span>
                      )}
                    </td>
                  </tr>
                ))}
                {variants.length === 0 ? (
                  <tr>
                    <td className="px-3 py-6 text-slate-500" colSpan={8}>No variants yet. Create a product first before adding variants.</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>

        {dialog === "product" ? (
          <section className="rounded-2xl bg-white p-6 shadow-sm">
            <ProductForm onSubmit={(values) => createProductMutation.mutate(values)} />
          </section>
        ) : null}
        {dialog === "variant" ? (
          <section className="rounded-2xl bg-white p-4 shadow-sm sm:p-6">
            <ProductVariantForm
              products={products}
              isSubmitting={createVariantMutation.isPending}
              submitError={createVariantMutation.isError ? safeApiErrorMessage(createVariantMutation.error, "Unable to create variant. Please try again.") : null}
              onSubmit={(values) => createVariantMutation.mutate(values)}
            />
          </section>
        ) : null}
        {archivingProduct ? (
          <ConfirmActionDialog title="Archive product?" description="Archiving this product hides it from the active catalog. Existing orders remain unchanged." actionLabel="Archive product" isSubmitting={archiveProductMutation.isPending} error={archiveProductMutation.isError ? safeApiErrorMessage(archiveProductMutation.error, "Unable to delete record. Please try again.") : null} onCancel={() => setArchivingProduct(null)} onConfirm={() => archiveProductMutation.mutate()} />
        ) : null}
        {archivingVariant ? (
          <ConfirmActionDialog title="Archive variant?" description="This variant will be hidden from active selectors. Inventory is not hard deleted, and historical order items remain unchanged." actionLabel="Archive variant" isSubmitting={archiveVariantMutation.isPending} error={archiveVariantMutation.isError ? safeApiErrorMessage(archiveVariantMutation.error, "This record cannot be deleted because it is used by other records.") : null} onCancel={() => setArchivingVariant(null)} onConfirm={() => archiveVariantMutation.mutate()} />
        ) : null}
        {editingProduct ? (
          <EditRecordDialog
            title="Edit product"
            fields={[
              { name: "sku", label: "SKU" },
              { name: "name", label: "Name" },
              { name: "category", label: "Category" },
              { name: "brand", label: "Brand" },
              { name: "description", label: "Description", type: "textarea" },
              { name: "is_active", label: "Active", type: "select", options: [{ value: "true", label: "Active" }, { value: "false", label: "Inactive" }] },
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
            title="Edit variant"
            fields={[
              { name: "sku", label: "Variant SKU" },
              { name: "color", label: "Color" },
              { name: "size", label: "Size" },
              { name: "price", label: "Selling price", type: "number" },
              { name: "barcode", label: "Barcode" },
              { name: "is_active", label: "Active", type: "select", options: [{ value: "true", label: "Active" }, { value: "false", label: "Inactive" }] },
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
