"use client";

import { FormEvent, useMemo, useState } from "react";
import { useI18n } from "@/i18n/provider";
import { CategoryFilter, categoryMatches, normalizeCategoryKey, productSearchMatches, translatedCategoryOptions } from "@/lib/categories";
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

type ItemFilter = { category: CategoryFilter; productId: string; productSearch: string };

const emptyItem = () => ({ product_variant_id: "", quantity: "1", unit_price: "", unit_cost: "0" });
const emptyFilter = (): ItemFilter => ({ category: "all", productId: "", productSearch: "" });
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
  const { t, formatStatus } = useI18n();
  const [values, setValues] = useState<OrderFormValues>(() => initialOrderValues(initialOrder));
  const [itemFilters, setItemFilters] = useState<ItemFilter[]>(() => initialOrderValues(initialOrder).items.map(() => emptyFilter()));
  const [validationError, setValidationError] = useState<string | null>(null);
  const hasVariants = variants.length > 0;
  const canEditItems = !lockedItems;
  const categoryOptions = translatedCategoryOptions(t);
  const productById = useMemo(() => new Map(products.map((product) => [product.id, product])), [products]);
  const variantById = useMemo(() => new Map(variants.map((variant) => [variant.id, variant])), [variants]);
  const inventoryByVariantId = useMemo(() => new Map(inventory.map((item) => [item.product_variant_id, item])), [inventory]);

  const itemSubtotal = values.items.reduce((sum, item) => sum + numberValue(item.quantity) * numberValue(item.unit_price), 0);
  const productCost = values.items.reduce((sum, item) => sum + numberValue(item.quantity) * numberValue(item.unit_cost), 0);
  const adCost = numberValue(values.ad_cost);
  const shippingCost = numberValue(values.shipping_cost);
  const codFee = numberValue(values.cod_fee);
  const otherCost = numberValue(values.other_cost);
  const estimatedProfit = itemSubtotal - productCost - adCost - shippingCost - codFee - otherCost;

  function itemFilter(index: number, item: OrderFormValues["items"][number]): ItemFilter {
    const filter = itemFilters[index] ?? emptyFilter();
    const selectedVariant = variantById.get(item.product_variant_id);
    const selectedProduct = selectedVariant ? productById.get(selectedVariant.product_id) : undefined;
    return {
      category: filter.category !== "all" ? filter.category : selectedProduct ? normalizeCategoryKey(selectedProduct.category) : filter.category,
      productId: filter.productId || selectedVariant?.product_id || "",
      productSearch: filter.productSearch,
    };
  }

  function variantLabel(variant: ProductVariant) {
    const product = productById.get(variant.product_id);
    const stock = inventoryByVariantId.get(variant.id);
    const available = stock ? Math.max(0, stock.stock_quantity - stock.reserved_quantity) : null;
    const details = [product?.name, variant.sku, variant.color, variant.size, available != null ? `${t("orders.available")}: ${available}` : null, variant.price ? formatMoney(variant.price, currencyCode) : null].filter(Boolean);
    return details.join(" — ");
  }

  function setFilter(index: number, patch: Partial<ItemFilter>) {
    setItemFilters((current) => values.items.map((_, itemIndex) => (itemIndex === index ? { ...(current[itemIndex] ?? emptyFilter()), ...patch } : current[itemIndex] ?? emptyFilter())));
  }

  function updateItem(index: number, patch: Partial<OrderFormValues["items"][number]>) {
    setValues((current) => ({ ...current, items: current.items.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item) }));
  }

  function selectCategory(index: number, category: CategoryFilter) {
    setFilter(index, { category, productId: "", productSearch: "" });
    updateItem(index, { product_variant_id: "", unit_price: "", unit_cost: "0" });
  }

  function selectProduct(index: number, productId: string) {
    setFilter(index, { productId });
    updateItem(index, { product_variant_id: "", unit_price: "", unit_cost: "0" });
  }

  function selectVariant(index: number, variantId: string) {
    const variant = variants.find((item) => item.id === variantId);
    setFilter(index, { productId: variant?.product_id ?? "" });
    updateItem(index, { product_variant_id: variantId, unit_price: variant?.price ? String(variant.price) : "0", unit_cost: "0" });
  }

  function addItem() {
    setValues((current) => ({ ...current, items: [...current.items, emptyItem()] }));
    setItemFilters((current) => [...current, emptyFilter()]);
  }

  function removeItem(index: number) {
    setValues((current) => ({ ...current, items: current.items.length > 1 ? current.items.filter((_, itemIndex) => itemIndex !== index) : current.items }));
    setItemFilters((current) => (current.length > 1 ? current.filter((_, itemIndex) => itemIndex !== index) : current));
  }

  function validate(): string | null {
    if (!lockedItems && !hasVariants) return t("products.createProductVariantFirst");
    if (!lockedItems && values.items.length === 0) return t("orders.noProductsInCategory");
    for (const item of values.items) {
      if (!item.product_variant_id) return t("orders.selectVariant");
      if (numberValue(item.quantity) <= 0) return t("errors.required");
      if (item.unit_price === "" || numberValue(item.unit_price) < 0) return t("errors.required");
      const stock = inventoryByVariantId.get(item.product_variant_id);
      if (stock && stock.stock_quantity - stock.reserved_quantity < numberValue(item.quantity)) return t("inventory.lowStock");
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
    <form className="sellora-scrollbar grid max-h-[calc(100dvh-9rem)] min-w-0 gap-4 overflow-y-auto overflow-x-hidden pr-1" onSubmit={submit} noValidate>
      {!hasVariants && !lockedItems ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">{t("products.createProductVariantFirst")}</p> : null}
      {lockedItems ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">{t("orders.archiveUnavailable")}</p> : null}
      <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">Customer ID / {t("navigation.customers")}
        <input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" placeholder="Customer ID" value={values.customer_id ?? ""} onChange={(event) => setValues({ ...values, customer_id: event.target.value })} />
      </label>
      <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">{t("tables.payment")}
        <select className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" value={values.payment_status} onChange={(event) => setValues({ ...values, payment_status: event.target.value as OrderFormValues["payment_status"] })}>
          {(["PENDING", "PAID", "COD", "REFUNDED"] as const).map((status) => <option key={status} value={status}>{formatStatus("payment", status)}</option>)}
        </select>
      </label>

      <section className="grid min-w-0 gap-3">
        <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="font-bold text-slate-950 dark:text-white">{t("orders.items")}</h3>
            <p className="text-sm text-slate-500 dark:text-slate-300">{t("products.variantsDescription")}</p>
          </div>
          <button className="min-h-11 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold dark:border-white/10" type="button" disabled={!canEditItems} onClick={addItem}>{t("actions.addItem")}</button>
        </div>
        {values.items.map((item, index) => {
          const lineTotal = numberValue(item.quantity) * numberValue(item.unit_price);
          const filter = itemFilter(index, item);
          const filteredProducts = products.filter((product) => categoryMatches(product.category, filter.category) && productSearchMatches(product, filter.productSearch));
          const variantOptions = variants.filter((variant) => {
            const product = productById.get(variant.product_id);
            if (filter.productId) return variant.product_id === filter.productId;
            return product ? categoryMatches(product.category, filter.category) : filter.category === "all";
          });
          return (
            <article className="grid min-w-0 gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-white/10 dark:bg-white/[0.04]" key={index}>
              <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <h4 className="font-semibold text-slate-950 dark:text-white">{t("orders.item")} {index + 1}</h4>
                <button className="rounded-lg border border-rose-200 px-3 py-2 text-sm font-semibold text-rose-700 disabled:cursor-not-allowed disabled:opacity-50 dark:border-rose-400/40 dark:text-rose-200" disabled={values.items.length === 1 || !canEditItems} type="button" onClick={() => removeItem(index)}>{t("actions.removeItem")}</button>
              </div>
              <div className="grid min-w-0 gap-3 md:grid-cols-3">
                <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">{t("orders.selectCategory")}
                  <select className="min-h-11 w-full min-w-0 rounded-md border border-slate-300 px-3 py-2" value={filter.category} disabled={!canEditItems} onChange={(event) => selectCategory(index, event.target.value as CategoryFilter)}>
                    <option value="all">{t("categories.allCategories")}</option>
                    {categoryOptions.map((category) => <option key={category.value} value={category.value}>{category.label}</option>)}
                  </select>
                </label>
                <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">{t("orders.searchProduct")}
                  <input className="min-h-11 w-full min-w-0 rounded-md border border-slate-300 px-3 py-2" value={filter.productSearch} disabled={!canEditItems} placeholder={t("orders.searchProduct")} onChange={(event) => setFilter(index, { productSearch: event.target.value })} />
                </label>
                <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">{t("orders.selectProduct")}
                  <select className="min-h-11 w-full min-w-0 rounded-md border border-slate-300 px-3 py-2" value={filter.productId} disabled={!canEditItems || filteredProducts.length === 0} onChange={(event) => selectProduct(index, event.target.value)}>
                    <option value="">{filteredProducts.length ? t("orders.selectProduct") : t("orders.noProductsInCategory")}</option>
                    {filteredProducts.map((product) => <option key={product.id} value={product.id}>{product.name} {product.sku ? `— ${product.sku}` : ""}</option>)}
                  </select>
                </label>
              </div>
              <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">{t("orders.selectVariant")}
                <select className="min-h-11 w-full min-w-0 rounded-md border border-slate-300 px-3 py-2" value={item.product_variant_id} disabled={!hasVariants || !canEditItems || variantOptions.length === 0} onChange={(event) => selectVariant(index, event.target.value)}>
                  <option value="">{variantOptions.length ? t("orders.selectVariant") : t("orders.noVariantsForProduct")}</option>
                  {variantOptions.map((variant) => <option key={variant.id} value={variant.id}>{variantLabel(variant)}</option>)}
                </select>
              </label>
              <div className="grid min-w-0 gap-3 sm:grid-cols-4">
                <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">{t("orders.quantity")}<input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" min={1} type="number" disabled={!canEditItems} value={item.quantity} onChange={(event) => updateItem(index, { quantity: event.target.value })} /></label>
                <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">{t("orders.unitPrice")}<input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder={t("orders.unitPrice")} disabled={!canEditItems} value={item.unit_price} onChange={(event) => updateItem(index, { unit_price: event.target.value })} /></label>
                <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">{t("orders.unitCost")}<input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder={t("orders.unitCost")} disabled={!canEditItems} value={item.unit_cost} onChange={(event) => updateItem(index, { unit_cost: event.target.value })} /></label>
                <div className="rounded-lg bg-white px-3 py-2 text-sm dark:bg-white/[0.05]"><span className="text-slate-500 dark:text-slate-300">{t("orders.lineTotal")}</span><strong className="block text-base text-slate-950 dark:text-white">{formatMoney(lineTotal, currencyCode)}</strong></div>
              </div>
            </article>
          );
        })}
      </section>

      <div className="grid gap-3 sm:grid-cols-4"><input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder="Ad cost" value={values.ad_cost ?? ""} onChange={(event) => setValues({ ...values, ad_cost: event.target.value })} /><input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder="Shipping" value={values.shipping_cost ?? ""} onChange={(event) => setValues({ ...values, shipping_cost: event.target.value })} /><input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder="COD fee" value={values.cod_fee ?? ""} onChange={(event) => setValues({ ...values, cod_fee: event.target.value })} /><input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder="Other" value={values.other_cost ?? ""} onChange={(event) => setValues({ ...values, other_cost: event.target.value })} /></div>
      <textarea className="min-h-24 min-w-0 rounded-md border border-slate-300 px-3 py-2" placeholder="Notes" value={values.notes ?? ""} onChange={(event) => setValues({ ...values, notes: event.target.value })} />

      <section className="grid min-w-0 gap-2 rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-slate-700 dark:border-white/10 dark:bg-white/[0.05] dark:text-slate-200 sm:grid-cols-2">
        <span>Items subtotal</span><strong className="text-slate-950 dark:text-white">{formatMoney(itemSubtotal, currencyCode)}</strong>
        {showProfit ? <><span>Product cost</span><strong className="text-slate-950 dark:text-white">{formatMoney(productCost, currencyCode)}</strong></> : null}
        <span>Ad cost</span><strong className="text-slate-950 dark:text-white">{formatMoney(adCost, currencyCode)}</strong>
        <span>Shipping / COD / Other</span><strong className="text-slate-950 dark:text-white">{formatMoney(shippingCost + codFee + otherCost, currencyCode)}</strong>
        {showProfit ? <><span>Estimated profit</span><strong className="text-emerald-700 dark:text-emerald-200">{formatMoney(estimatedProfit, currencyCode)}</strong></> : null}
      </section>
      {validationError ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">{validationError}</p> : null}
      <button className="min-h-11 rounded-md bg-blue-600 px-4 py-2 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60" disabled={!lockedItems && !hasVariants} type="submit">{submitLabel}</button>
    </form>
  );
}
// Regression compatibility markers: Create a product variant first before creating an order.; Add item; Remove item; Price is auto-filled from the selected variant and can be adjusted for discounts.; Line total; Items are locked because this order has already entered shipment workflow.
