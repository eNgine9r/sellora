"use client";

import { FormEvent, useState } from "react";
import { buildProductVariantCreatePayload } from "@/lib/payload-builders";
import { ProductVariantCreatePayload } from "@/services/products";
import { Product } from "@/types/products";

export type ProductVariantFormValues = {
  product_id: string;
  sku: string;
  color?: string;
  size?: string;
  price?: string;
  initial_stock_quantity?: string;
  minimum_quantity?: string;
};

export function ProductVariantForm({ products, onSubmit, isSubmitting = false, submitError }: { products: Product[]; onSubmit: (values: ProductVariantCreatePayload) => void; isSubmitting?: boolean; submitError?: string | null }) {
  const [values, setValues] = useState<ProductVariantFormValues>({ product_id: "", sku: "", initial_stock_quantity: "0", minimum_quantity: "0" });
  const [validationError, setValidationError] = useState<string | null>(null);
  const hasProducts = products.length > 0;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!hasProducts) {
      setValidationError("Create a product first before adding variants.");
      return;
    }
    const payload = buildProductVariantCreatePayload(values);
    if (!payload.product_id) {
      setValidationError("Please select a product.");
      return;
    }
    if (!payload.sku) {
      setValidationError("Variant SKU is required.");
      return;
    }
    setValidationError(null);
    onSubmit(payload);
  }

  return (
    <form className="grid w-full min-w-0 gap-4 overflow-x-hidden" onSubmit={submit} noValidate>
      {!hasProducts ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">Create a product first before adding variants.</p> : null}
      <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">
        Product
        <select className="min-h-11 w-full min-w-0 rounded-md border border-slate-300 px-3 py-2" value={values.product_id} onChange={(event) => setValues({ ...values, product_id: event.target.value })} disabled={!hasProducts}>
          <option value="">Select product</option>
          {products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}
        </select>
      </label>
      <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">
        Variant SKU
        <input className="min-h-11 w-full min-w-0 rounded-md border border-slate-300 px-3 py-2" placeholder="Variant SKU" value={values.sku} onChange={(event) => setValues({ ...values, sku: event.target.value })} />
      </label>
      <div className="grid min-w-0 gap-4 sm:grid-cols-2">
        <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">Color<input className="min-h-11 w-full min-w-0 rounded-md border border-slate-300 px-3 py-2" placeholder="Color" value={values.color ?? ""} onChange={(event) => setValues({ ...values, color: event.target.value })} /></label>
        <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">Size<input className="min-h-11 w-full min-w-0 rounded-md border border-slate-300 px-3 py-2" placeholder="Size" value={values.size ?? ""} onChange={(event) => setValues({ ...values, size: event.target.value })} /></label>
      </div>
      <div className="grid min-w-0 gap-4 [grid-template-columns:repeat(auto-fit,minmax(180px,1fr))]">
        <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">Price<input className="min-h-11 w-full min-w-0 rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder="Price" value={values.price ?? ""} onChange={(event) => setValues({ ...values, price: event.target.value })} /></label>
        <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">Initial stock<input className="min-h-11 w-full min-w-0 rounded-md border border-slate-300 px-3 py-2" min={0} type="number" placeholder="Initial stock" value={values.initial_stock_quantity ?? "0"} onChange={(event) => setValues({ ...values, initial_stock_quantity: event.target.value })} /></label>
        <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">Minimum stock<input className="min-h-11 w-full min-w-0 rounded-md border border-slate-300 px-3 py-2" min={0} type="number" placeholder="Minimum stock" value={values.minimum_quantity ?? "0"} onChange={(event) => setValues({ ...values, minimum_quantity: event.target.value })} /></label>
      </div>
      {validationError ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">{validationError}</p> : null}
      {submitError ? <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700">{submitError}</p> : null}
      <button className="min-h-11 w-full rounded-md bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60" disabled={isSubmitting || !hasProducts} type="submit">
        {isSubmitting ? "Creating…" : "Create variant"}
      </button>
    </form>
  );
}
