"use client";

import { FormEvent, useState } from "react";
import { buildOrderCreatePayload } from "@/lib/payload-builders";
import { OrderCreatePayload } from "@/services/orders";
import { ProductVariant } from "@/types/products";

export type OrderFormValues = {
  customer_id?: string;
  payment_status: "PENDING" | "PAID" | "COD" | "REFUNDED";
  items: { product_variant_id: string; quantity: string; unit_price: string; unit_cost: string }[];
  ad_cost?: string;
  shipping_cost?: string;
  cod_fee?: string;
  other_cost?: string;
  notes?: string;
};

export function OrderForm({ variants, onSubmit }: { variants: ProductVariant[]; onSubmit: (values: OrderCreatePayload) => void }) {
  const [values, setValues] = useState<OrderFormValues>({ payment_status: "PENDING", items: [{ product_variant_id: "", quantity: "1", unit_price: "0", unit_cost: "0" }] });
  const [validationError, setValidationError] = useState<string | null>(null);
  const item = values.items[0];
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = buildOrderCreatePayload(values);
    if (!payload.items[0]?.product_variant_id) {
      setValidationError("Product variant is required.");
      return;
    }
    setValidationError(null);
    onSubmit(payload);
  }
  return (
    <form className="grid gap-3" onSubmit={submit}>
      <input className="rounded-md border border-slate-300 px-3 py-2" placeholder="Customer ID (optional)" value={values.customer_id ?? ""} onChange={(event) => setValues({ ...values, customer_id: event.target.value })} />
      <select className="rounded-md border border-slate-300 px-3 py-2" required value={item.product_variant_id} onChange={(event) => setValues({ ...values, items: [{ ...item, product_variant_id: event.target.value }] })}><option value="">Select variant</option>{variants.map((variant) => <option key={variant.id} value={variant.id}>{variant.sku}</option>)}</select>
      <div className="grid gap-3 md:grid-cols-3"><input className="rounded-md border border-slate-300 px-3 py-2" min={1} type="number" value={item.quantity} onChange={(event) => setValues({ ...values, items: [{ ...item, quantity: event.target.value }] })} /><input className="rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder="Unit price" value={item.unit_price} onChange={(event) => setValues({ ...values, items: [{ ...item, unit_price: event.target.value }] })} /><input className="rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder="Unit cost" value={item.unit_cost} onChange={(event) => setValues({ ...values, items: [{ ...item, unit_cost: event.target.value }] })} /></div>
      <div className="grid gap-3 md:grid-cols-4"><input className="rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder="Ad cost" value={values.ad_cost ?? ""} onChange={(event) => setValues({ ...values, ad_cost: event.target.value })} /><input className="rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder="Shipping" value={values.shipping_cost ?? ""} onChange={(event) => setValues({ ...values, shipping_cost: event.target.value })} /><input className="rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder="COD fee" value={values.cod_fee ?? ""} onChange={(event) => setValues({ ...values, cod_fee: event.target.value })} /><input className="rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder="Other" value={values.other_cost ?? ""} onChange={(event) => setValues({ ...values, other_cost: event.target.value })} /></div>
      {validationError ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">{validationError}</p> : null}
      <button className="rounded-md bg-blue-600 px-4 py-2 font-semibold text-white" type="submit">Create order</button>
    </form>
  );
}
