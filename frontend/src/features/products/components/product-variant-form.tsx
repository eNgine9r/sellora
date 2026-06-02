"use client";

import { FormEvent, useState } from "react";
import { ProductVariantCreatePayload } from "@/services/products";
import { Product } from "@/types/products";

export function ProductVariantForm({ products, onSubmit }: { products: Product[]; onSubmit: (values: ProductVariantCreatePayload) => void }) {
  const [values, setValues] = useState<ProductVariantCreatePayload>({ product_id: "", sku: "", initial_stock_quantity: 0, minimum_quantity: 0 });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit(values);
    setValues({ product_id: "", sku: "", initial_stock_quantity: 0, minimum_quantity: 0 });
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
        <input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Price" value={values.price ?? ""} onChange={(event) => setValues({ ...values, price: event.target.value })} />
        <input className="rounded-md border border-slate-300 px-3 py-2" min={0} type="number" placeholder="Initial stock" value={values.initial_stock_quantity ?? 0} onChange={(event) => setValues({ ...values, initial_stock_quantity: Number(event.target.value) })} />
        <input className="rounded-md border border-slate-300 px-3 py-2" min={0} type="number" placeholder="Minimum stock" value={values.minimum_quantity ?? 0} onChange={(event) => setValues({ ...values, minimum_quantity: Number(event.target.value) })} />
      </div>
      <button className="rounded-md bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700" type="submit">Create variant</button>
    </form>
  );
}
