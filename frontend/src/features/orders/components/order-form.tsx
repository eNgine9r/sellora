"use client";

import { FormEvent, useState } from "react";
import { OrderCreatePayload } from "@/services/orders";
import { ProductVariant } from "@/types/products";

export function OrderForm({ variants, onSubmit }: { variants: ProductVariant[]; onSubmit: (values: OrderCreatePayload) => void }) {
  const [values, setValues] = useState<OrderCreatePayload>({ payment_status: "PENDING", items: [{ product_variant_id: "", quantity: 1, unit_price: "0", unit_cost: "0" }] });
  const item = values.items[0];
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); onSubmit(values); }
  return (
    <form className="grid gap-3" onSubmit={submit}>
      <input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Customer ID (optional)" value={values.customer_id ?? ""} onChange={(event) => setValues({ ...values, customer_id: event.target.value || undefined })} />
      <select className="rounded-md border border-slate-300 px-3 py-2" required value={item.product_variant_id} onChange={(event) => setValues({ ...values, items: [{ ...item, product_variant_id: event.target.value }] })}><option value="">Select variant</option>{variants.map((variant) => <option key={variant.id} value={variant.id}>{variant.sku}</option>)}</select>
      <div className="grid gap-3 md:grid-cols-3"><input className="rounded-md border border-slate-300 px-3 py-2" min={1} type="number" value={item.quantity} onChange={(event) => setValues({ ...values, items: [{ ...item, quantity: Number(event.target.value) }] })} /><input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Unit price" value={item.unit_price} onChange={(event) => setValues({ ...values, items: [{ ...item, unit_price: event.target.value }] })} /><input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Unit cost" value={item.unit_cost ?? "0"} onChange={(event) => setValues({ ...values, items: [{ ...item, unit_cost: event.target.value }] })} /></div>
      <div className="grid gap-3 md:grid-cols-4"><input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Ad cost" onChange={(event) => setValues({ ...values, ad_cost: event.target.value })} /><input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Shipping" onChange={(event) => setValues({ ...values, shipping_cost: event.target.value })} /><input className="rounded-md border border-slate-300 px-3 py-2" placeholder="COD fee" onChange={(event) => setValues({ ...values, cod_fee: event.target.value })} /><input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Other" onChange={(event) => setValues({ ...values, other_cost: event.target.value })} /></div>
      <button className="rounded-md bg-blue-600 px-4 py-2 font-semibold text-white" type="submit">Create order</button>
    </form>
  );
}
