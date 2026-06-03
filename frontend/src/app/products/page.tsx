"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ProductForm } from "@/features/products/components/product-form";
import { ProductTable } from "@/features/products/components/product-table";
import { ProductVariantForm } from "@/features/products/components/product-variant-form";
import { useAuth } from "@/hooks/use-auth";
import { safeApiErrorMessage } from "@/services/api";
import { createProduct, createProductVariant, fetchProducts } from "@/services/products";

export default function ProductsPage() {
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspaceId, status: authStatus } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const [search, setSearch] = useState("");
  const [dialog, setDialog] = useState<"product" | "variant" | null>(null);
  const enabled = authStatus === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);

  const productsQuery = useQuery({
    queryKey: ["products", workspaceId, search],
    queryFn: () => fetchProducts(workspaceId, search.trim() || undefined, undefined),
    enabled,
  });
  const createProductMutation = useMutation({
    mutationFn: (values: Parameters<typeof createProduct>[1]) => createProduct(workspaceId, values, undefined),
    onSuccess: () => {
      setDialog(null);
      queryClient.invalidateQueries({ queryKey: ["products", workspaceId] });
    },
  });
  const createVariantMutation = useMutation({
    mutationFn: (values: Parameters<typeof createProductVariant>[1]) => createProductVariant(workspaceId, values, undefined),
    onSuccess: () => {
      setDialog(null);
      queryClient.invalidateQueries({ queryKey: ["products", workspaceId] });
      queryClient.invalidateQueries({ queryKey: ["product-variants", workspaceId] });
      queryClient.invalidateQueries({ queryKey: ["inventory", workspaceId] });
    },
  });

  const productCreateError = createProductMutation.isError ? safeApiErrorMessage(createProductMutation.error, "Unable to create product. Please try again.") : null;
  const variantCreateError = createVariantMutation.isError ? safeApiErrorMessage(createVariantMutation.error, "Unable to create variant. Please try again.") : null;
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
          <div className="flex gap-3">
            <button className="rounded-lg border border-slate-300 px-4 py-2 font-semibold disabled:cursor-not-allowed disabled:opacity-60" disabled={!enabled} onClick={() => setDialog("variant")}>Create variant</button>
            <button className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60" disabled={!enabled} onClick={() => setDialog("product")}>Create product</button>
          </div>
        </header>
        <section className="grid gap-3 rounded-2xl bg-white p-4 shadow-sm md:grid-cols-3">
          <input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Search products" value={search} onChange={(event) => setSearch(event.target.value)} />
        </section>
        {listError ? <p className="rounded-lg bg-rose-50 p-4 text-rose-700">{listError}</p> : null}
        <ProductTable products={productsQuery.data ?? []} />
        {dialog ? (
          <div className="fixed inset-0 grid place-items-center bg-slate-950/40 p-4">
            <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-xl">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-xl font-bold">{dialog === "product" ? "Create product" : "Create variant"}</h2>
                <button className="text-slate-500" onClick={() => setDialog(null)}>Close</button>
              </div>
              {dialog === "product" ? (
                <ProductForm isSubmitting={createProductMutation.isPending} submitError={productCreateError} onSubmit={(values) => createProductMutation.mutate(values)} />
              ) : (
                <ProductVariantForm products={productsQuery.data ?? []} isSubmitting={createVariantMutation.isPending} submitError={variantCreateError} onSubmit={(values) => createVariantMutation.mutate(values)} />
              )}
            </div>
          </div>
        ) : null}
      </div>
    </main>
  );
}
