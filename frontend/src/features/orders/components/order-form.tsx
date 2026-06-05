"use client";

import { FormEvent, useMemo, useState } from "react";
import { buildOrderCreatePayload } from "@/lib/payload-builders";
import { formatMoney } from "@/lib/currency";
import { OrderCreatePayload } from "@/services/orders";
import { Order } from "@/types/orders";
import { Inventory, Product, ProductVariant } from "@/types/products";

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

const emptyItem = () => ({ product_variant_id: "", quantity: "1", unit_price: "", unit_cost: "0" });
const numberValue = (value?: string | number | null) => {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
};
function initialOrderValues(order?: Order | null): OrderFormValues {
  return {
    customer_id: order?.customer_id ?? undefined,
    payment_status: order?.payment_status ?? "PENDING",
    items: order?.items.length ? order.items.map((item) => ({ product_variant_id: item.product_variant_id, quantity: String(item.quantity), unit_price: String(item.unit_price), unit_cost: String(item.unit_cost) })) : [emptyItem()],
    ad_cost: order ? String(order.ad_cost) : undefined,
    shipping_cost: order ? String(order.shipping_cost) : undefined,
    cod_fee: order ? String(order.cod_fee) : undefined,
    other_cost: order ? String(order.other_cost) : undefined,
    notes: order?.notes ?? undefined,
  };
}

export function OrderForm({ variants, products = [], inventory = [], showProfit = false, currencyCode = "UAH", initialOrder, lockedItems = false, submitLabel = "Create order", onSubmit }: { variants: ProductVariant[]; products?: Product[]; inventory?: Inventory[]; showProfit?: boolean; currencyCode?: string; initialOrder?: Order | null; lockedItems?: boolean; submitLabel?: string; onSubmit: (values: Partial<OrderCreatePayload>) => void }) {
  const [values, setValues] = useState<OrderFormValues>(() => initialOrderValues(initialOrder));
  const [validationError, setValidationError] = useState<string | null>(null);
  const hasVariants = variants.length > 0;
  const canEditItems = !lockedItems;
  const productById = useMemo(() => new Map(products.map((product) => [product.id, product])), [products]);
  const inventoryByVariantId = useMemo(() => new Map(inventory.map((item) => [item.product_variant_id, item])), [inventory]);

  const itemSubtotal = values.items.reduce((sum, item) => sum + numberValue(item.quantity) * numberValue(item.unit_price), 0);
  const productCost = values.items.reduce((sum, item) => sum + numberValue(item.quantity) * numberValue(item.unit_cost), 0);
  const adCost = numberValue(values.ad_cost);
  const shippingCost = numberValue(values.shipping_cost);
  const codFee = numberValue(values.cod_fee);
  const otherCost = numberValue(values.other_cost);
  const estimatedProfit = itemSubtotal - productCost - adCost - shippingCost - codFee - otherCost;

  function variantLabel(variant: ProductVariant) {
    const product = productById.get(variant.product_id);
    const stock = inventoryByVariantId.get(variant.id);
    const details = [product?.name, variant.sku, variant.color, variant.size ? `Size ${variant.size}` : null, stock ? `Available ${Math.max(0, stock.stock_quantity - stock.reserved_quantity)}` : null, variant.price ? formatMoney(variant.price, currencyCode) : null].filter(Boolean);
    return details.join(" — ");
  }

  function updateItem(index: number, patch: Partial<OrderFormValues["items"][number]>) {
    setValues((current) => ({ ...current, items: current.items.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item) }));
  }

  function selectVariant(index: number, variantId: string) {
    const variant = variants.find((item) => item.id === variantId);
    updateItem(index, { product_variant_id: variantId, unit_price: variant?.price ? String(variant.price) : "0", unit_cost: "0" });
  }

  function addItem() {
    setValues((current) => ({ ...current, items: [...current.items, emptyItem()] }));
  }

  function removeItem(index: number) {
    setValues((current) => ({ ...current, items: current.items.length > 1 ? current.items.filter((_, itemIndex) => itemIndex !== index) : current.items }));
  }

  function validate(): string | null {
    if (!lockedItems && !hasVariants) return "Create a product variant first before creating an order.";
    if (!lockedItems && values.items.length === 0) return "Add at least one item.";
    for (const item of values.items) {
      if (!item.product_variant_id) return "Please select a variant.";
      if (numberValue(item.quantity) <= 0) return "Quantity must be greater than 0.";
      if (item.unit_price === "" || numberValue(item.unit_price) < 0) return "Unit price is required.";
      const stock = inventoryByVariantId.get(item.product_variant_id);
      if (stock && stock.stock_quantity - stock.reserved_quantity < numberValue(item.quantity)) return "This variant is out of stock.";
    }
    return null;
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const error = validate();
    if (error) {
      setValidationError(error);
      return;
    }
    setValidationError(null);
    const payload = buildOrderCreatePayload(values);
    if (lockedItems) delete (payload as Partial<OrderCreatePayload>).items;
    onSubmit(payload);
  }

  return (
    <form className="grid max-h-[calc(100dvh-9rem)] min-w-0 gap-4 overflow-y-auto overflow-x-hidden pr-1" onSubmit={submit} noValidate>
      {!hasVariants && !lockedItems ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">Create a product variant first before creating an order.</p> : null}
      {lockedItems ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">Items are locked because this order has already entered shipment workflow.</p> : null}
      <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">Customer ID / Customer
        <input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" placeholder="Customer ID (optional)" value={values.customer_id ?? ""} onChange={(event) => setValues({ ...values, customer_id: event.target.value })} />
      </label>
      <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">Payment status
        <select className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" value={values.payment_status} onChange={(event) => setValues({ ...values, payment_status: event.target.value as OrderFormValues["payment_status"] })}>
          {(["PENDING", "PAID", "COD", "REFUNDED"] as const).map((status) => <option key={status} value={status}>{status}</option>)}
        </select>
      </label>

      <section className="grid min-w-0 gap-3">
        <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="font-bold text-slate-950">Order items</h3>
            <p className="text-sm text-slate-500">Price is auto-filled from the selected variant and can be adjusted for discounts.</p>
          </div>
          <button className="min-h-11 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold" type="button" disabled={!canEditItems} onClick={addItem}>Add item</button>
        </div>
        {values.items.map((item, index) => {
          const lineTotal = numberValue(item.quantity) * numberValue(item.unit_price);
          return (
            <article className="grid min-w-0 gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3" key={index}>
              <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <h4 className="font-semibold">Item {index + 1}</h4>
                <button className="rounded-lg border border-rose-200 px-3 py-2 text-sm font-semibold text-rose-700 disabled:cursor-not-allowed disabled:opacity-50" disabled={values.items.length === 1 || !canEditItems} type="button" onClick={() => removeItem(index)}>Remove item</button>
              </div>
              <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">Variant
                <select className="min-h-11 w-full min-w-0 rounded-md border border-slate-300 px-3 py-2" value={item.product_variant_id} disabled={!hasVariants || !canEditItems} onChange={(event) => selectVariant(index, event.target.value)}>
                  <option value="">Select variant</option>
                  {variants.map((variant) => <option key={variant.id} value={variant.id}>{variantLabel(variant)}</option>)}
                </select>
              </label>
              <div className="grid min-w-0 gap-3 sm:grid-cols-4">
                <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">Quantity<input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" min={1} type="number" disabled={!canEditItems} value={item.quantity} onChange={(event) => updateItem(index, { quantity: event.target.value })} /></label>
                <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">Unit price<input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder="Unit price" disabled={!canEditItems} value={item.unit_price} onChange={(event) => updateItem(index, { unit_price: event.target.value })} /></label>
                <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">Unit cost<input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder="Unit cost" disabled={!canEditItems} value={item.unit_cost} onChange={(event) => updateItem(index, { unit_cost: event.target.value })} /></label>
                <div className="rounded-lg bg-white px-3 py-2 text-sm"><span className="text-slate-500">Line total</span><strong className="block text-base">{formatMoney(lineTotal, currencyCode)}</strong></div>
              </div>
            </article>
          );
        })}
      </section>

      <div className="grid gap-3 sm:grid-cols-4"><input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder="Ad cost" value={values.ad_cost ?? ""} onChange={(event) => setValues({ ...values, ad_cost: event.target.value })} /><input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder="Shipping" value={values.shipping_cost ?? ""} onChange={(event) => setValues({ ...values, shipping_cost: event.target.value })} /><input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder="COD fee" value={values.cod_fee ?? ""} onChange={(event) => setValues({ ...values, cod_fee: event.target.value })} /><input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder="Other" value={values.other_cost ?? ""} onChange={(event) => setValues({ ...values, other_cost: event.target.value })} /></div>
      <textarea className="min-h-24 min-w-0 rounded-md border border-slate-300 px-3 py-2" placeholder="Notes" value={values.notes ?? ""} onChange={(event) => setValues({ ...values, notes: event.target.value })} />

      <section className="grid min-w-0 gap-2 rounded-xl bg-blue-50 p-4 text-sm text-slate-700 sm:grid-cols-2">
        <span>Items subtotal</span><strong>{formatMoney(itemSubtotal, currencyCode)}</strong>
        {showProfit ? <><span>Product cost</span><strong>{formatMoney(productCost, currencyCode)}</strong></> : null}
        <span>Ad cost</span><strong>{formatMoney(adCost, currencyCode)}</strong>
        <span>Shipping / COD / Other</span><strong>{formatMoney(shippingCost + codFee + otherCost, currencyCode)}</strong>
        {showProfit ? <><span>Estimated profit</span><strong>{formatMoney(estimatedProfit, currencyCode)}</strong></> : null}
      </section>
      {validationError ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">{validationError}</p> : null}
      <button className="min-h-11 rounded-md bg-blue-600 px-4 py-2 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60" disabled={!lockedItems && !hasVariants} type="submit">{submitLabel}</button>
    </form>
  );
}
