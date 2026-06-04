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

export function ProductVariantForm({
  products,
  onSubmit,
  isSubmitting = false,
  submitError,
}: {
  products: Product[];
  onSubmit: (values: ProductVariantCreatePayload) => void;
  isSubmitting?: boolean;
  submitError?: string | null;
}) {
  const [values, setValues] = useState<ProductVariantFormValues>({ product_id: "", sku: "", initial_stock_quantity: "0", minimum_quantity: "0" });
  const [validationError, setValidationError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = buildProductVariantCreatePayload(values);
    if (!payload.product_id) {
      setValidationError("Product is required.");
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
    <form className="grid gap-4" onSubmit={submit}>
      <select className="rounded-md border border-slate-300 px-3 py-2" required value={values.product_id} onChange={(event) => setValues({ ...values, product_id: event.target.value })}>
        <option value="">Select product</option>
        {products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}
      </select>
      <input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Variant SKU" required value={values.sku} onChange={(event) => setValues({ ...values, sku: event.target.value })} />
      <div className="grid gap-4 md:grid-cols-2">
        <input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Color" value={values.color ?? ""} onChange={(event) => setValues({ ...values, color: event.target.value })} />
        <input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Size" value={values.size ?? ""} onChange={(event) => setValues({ ...values, size: event.target.value })} />
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <input className="rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder="Price" value={values.price ?? ""} onChange={(event) => setValues({ ...values, price: event.target.value })} />
        <input className="rounded-md border border-slate-300 px-3 py-2" min={0} type="number" placeholder="Initial stock" value={values.initial_stock_quantity ?? "0"} onChange={(event) => setValues({ ...values, initial_stock_quantity: event.target.value })} />
        <input className="rounded-md border border-slate-300 px-3 py-2" min={0} type="number" placeholder="Minimum stock" value={values.minimum_quantity ?? "0"} onChange={(event) => setValues({ ...values, minimum_quantity: event.target.value })} />
      </div>
      {validationError ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">{validationError}</p> : null}
      {submitError ? <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700">{submitError}</p> : null}
      <button className="rounded-md bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Creating…" : "Create variant"}
      </button>
    </form>
  );
}
