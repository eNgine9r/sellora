"use client";

import { FormEvent, useMemo, useState } from "react";
import { useI18n } from "@/i18n/provider";
import {
  CategoryFilter,
  categoryMatches,
  displayCategory,
  normalizeCategoryKey,
  productSearchMatches,
  translatedCategoryOptions,
} from "@/lib/categories";
import { buildOrderCreatePayload } from "@/lib/payload-builders";
import { formatMoney } from "@/lib/currency";
import { CustomerCreatePayload } from "@/services/crm";
import { OrderCreatePayload } from "@/services/orders";
import { Customer } from "@/types/crm";
import { Order } from "@/types/orders";
import { Inventory, Product, ProductVariant } from "@/types/products";

export type OrderFormValues = {
  customer_id?: string;
  payment_status: "PENDING" | "PAID" | "COD" | "REFUNDED";
  items: {
    product_variant_id: string;
    quantity: string;
    unit_price: string;
    unit_cost: string;
  }[];
  ad_cost?: string;
  shipping_cost?: string;
  cod_fee?: string;
  other_cost?: string;
  notes?: string;
};

type ItemFilter = {
  category: CategoryFilter;
  productId: string;
  productSearch: string;
};

const emptyItem = () => ({
  product_variant_id: "",
  quantity: "1",
  unit_price: "",
  unit_cost: "0",
});
const emptyFilter = (): ItemFilter => ({
  category: "all",
  productId: "",
  productSearch: "",
});
const MAX_PRODUCT_SELECTOR_OPTIONS = 30;
const MAX_CUSTOMER_SELECTOR_OPTIONS = 8;

const numberValue = (value?: string | number | null) => {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
};
function initialOrderValues(order?: Order | null): OrderFormValues {
  return {
    customer_id: order?.customer_id ?? undefined,
    payment_status: order?.payment_status ?? "PENDING",
    items: order?.items.length
      ? order.items.map((item) => ({
          product_variant_id: item.product_variant_id,
          quantity: String(item.quantity),
          unit_price: String(item.unit_price),
          unit_cost: String(item.unit_cost),
        }))
      : [emptyItem()],
    ad_cost: order ? String(order.ad_cost) : undefined,
    shipping_cost: order ? String(order.shipping_cost) : undefined,
    cod_fee: order ? String(order.cod_fee) : undefined,
    other_cost: order ? String(order.other_cost) : undefined,
    notes: order?.notes ?? undefined,
  };
}

export function OrderForm({
  variants,
  products = [],
  inventory = [],
  customers = [],
  showProfit = false,
  currencyCode = "UAH",
  initialOrder,
  lockedItems = false,
  submitLabel = "Create order",
  isCreatingCustomer = false,
  onCreateCustomer,
  onSubmit,
}: {
  variants: ProductVariant[];
  products?: Product[];
  inventory?: Inventory[];
  customers?: Customer[];
  showProfit?: boolean;
  currencyCode?: string;
  initialOrder?: Order | null;
  lockedItems?: boolean;
  submitLabel?: string;
  isCreatingCustomer?: boolean;
  onCreateCustomer?: (payload: CustomerCreatePayload) => Promise<Customer>;
  onSubmit: (values: Partial<OrderCreatePayload>) => void;
}) {
  const { t, formatStatus } = useI18n();
  const [values, setValues] = useState<OrderFormValues>(() =>
    initialOrderValues(initialOrder),
  );
  const [itemFilters, setItemFilters] = useState<ItemFilter[]>(() =>
    initialOrderValues(initialOrder).items.map(() => emptyFilter()),
  );
  const [validationError, setValidationError] = useState<string | null>(null);
  const [customerSearch, setCustomerSearch] = useState("");
  const [isQuickCreateOpen, setIsQuickCreateOpen] = useState(false);
  const [quickCustomer, setQuickCustomer] = useState({
    name: "",
    phone: "",
    instagram_username: "",
  });
  const [quickCustomerError, setQuickCustomerError] = useState<string | null>(
    null,
  );
  const hasVariants = variants.length > 0;
  const canEditItems = !lockedItems;
  const categoryOptions = translatedCategoryOptions(t);
  const productById = useMemo(
    () => new Map(products.map((product) => [product.id, product])),
    [products],
  );
  const variantById = useMemo(
    () => new Map(variants.map((variant) => [variant.id, variant])),
    [variants],
  );
  const inventoryByVariantId = useMemo(
    () => new Map(inventory.map((item) => [item.product_variant_id, item])),
    [inventory],
  );
  const selectedCustomer = useMemo(
    () =>
      customers.find((customer) => customer.id === values.customer_id) ?? null,
    [customers, values.customer_id],
  );
  const filteredCustomers = useMemo(() => {
    const normalized = customerSearch.trim().toLowerCase();
    const rows = normalized
      ? customers.filter((customer) =>
          [customer.name, customer.phone, customer.instagram_username].some(
            (value) => value?.toLowerCase().includes(normalized),
          ),
        )
      : customers;
    return rows.slice(0, MAX_CUSTOMER_SELECTOR_OPTIONS);
  }, [customers, customerSearch]);

  const itemSubtotal = values.items.reduce(
    (sum, item) =>
      sum + numberValue(item.quantity) * numberValue(item.unit_price),
    0,
  );
  const productCost = values.items.reduce(
    (sum, item) =>
      sum + numberValue(item.quantity) * numberValue(item.unit_cost),
    0,
  );
  const adCost = numberValue(values.ad_cost);
  const shippingCost = numberValue(values.shipping_cost);
  const codFee = numberValue(values.cod_fee);
  const otherCost = numberValue(values.other_cost);
  const estimatedProfit =
    itemSubtotal - productCost - adCost - shippingCost - codFee - otherCost;

  function itemFilter(
    index: number,
    item: OrderFormValues["items"][number],
  ): ItemFilter {
    const filter = itemFilters[index] ?? emptyFilter();
    const selectedVariant = variantById.get(item.product_variant_id);
    const selectedProduct = selectedVariant
      ? productById.get(selectedVariant.product_id)
      : undefined;
    return {
      category:
        filter.category !== "all"
          ? filter.category
          : selectedProduct
            ? normalizeCategoryKey(selectedProduct.category)
            : filter.category,
      productId: filter.productId || selectedVariant?.product_id || "",
      productSearch: filter.productSearch,
    };
  }

  function productImage(product: Product) {
    return (
      product.images.find((image) => image.is_primary) ?? product.images[0]
    );
  }

  function productSummary(product: Product) {
    const productVariants = variants.filter(
      (variant) => variant.product_id === product.id,
    );
    const available = productVariants.reduce((sum, variant) => {
      const stock = inventoryByVariantId.get(variant.id);
      return (
        sum +
        (stock
          ? Math.max(0, stock.stock_quantity - stock.reserved_quantity)
          : 0)
      );
    }, 0);
    const firstPrice = productVariants.find((variant) => variant.price)?.price;
    return [
      product.sku,
      displayCategory(product.category, t),
      `${t("orders.productOption.available")}: ${available}`,
      firstPrice
        ? `${t("orders.productOption.price")}: ${formatMoney(firstPrice, currencyCode)}`
        : null,
    ]
      .filter(Boolean)
      .join(" · ");
  }

  function variantLabel(variant: ProductVariant) {
    const product = productById.get(variant.product_id);
    const stock = inventoryByVariantId.get(variant.id);
    const available = stock
      ? Math.max(0, stock.stock_quantity - stock.reserved_quantity)
      : null;
    const details = [
      product?.name,
      variant.sku,
      variant.color,
      variant.size,
      available != null ? `${t("orders.available")}: ${available}` : null,
      variant.price ? formatMoney(variant.price, currencyCode) : null,
    ].filter(Boolean);
    return details.join(" — ");
  }

  function setFilter(index: number, patch: Partial<ItemFilter>) {
    setItemFilters((current) =>
      values.items.map((_, itemIndex) =>
        itemIndex === index
          ? { ...(current[itemIndex] ?? emptyFilter()), ...patch }
          : (current[itemIndex] ?? emptyFilter()),
      ),
    );
  }

  function updateItem(
    index: number,
    patch: Partial<OrderFormValues["items"][number]>,
  ) {
    setValues((current) => ({
      ...current,
      items: current.items.map((item, itemIndex) =>
        itemIndex === index ? { ...item, ...patch } : item,
      ),
    }));
  }

  function selectCategory(index: number, category: CategoryFilter) {
    setFilter(index, { category, productId: "", productSearch: "" });
    updateItem(index, {
      product_variant_id: "",
      unit_price: "",
      unit_cost: "0",
    });
  }

  function selectProduct(index: number, productId: string) {
    setFilter(index, { productId });
    updateItem(index, {
      product_variant_id: "",
      unit_price: "",
      unit_cost: "0",
    });
  }

  function selectVariant(index: number, variantId: string) {
    const variant = variants.find((item) => item.id === variantId);
    setFilter(index, { productId: variant?.product_id ?? "" });
    updateItem(index, {
      product_variant_id: variantId,
      unit_price: variant?.price ? String(variant.price) : "0",
      unit_cost: "0",
    });
  }

  function addItem() {
    setValues((current) => ({
      ...current,
      items: [...current.items, emptyItem()],
    }));
    setItemFilters((current) => [...current, emptyFilter()]);
  }

  function removeItem(index: number) {
    setValues((current) => ({
      ...current,
      items:
        current.items.length > 1
          ? current.items.filter((_, itemIndex) => itemIndex !== index)
          : current.items,
    }));
    setItemFilters((current) =>
      current.length > 1
        ? current.filter((_, itemIndex) => itemIndex !== index)
        : current,
    );
  }

  function validate(): string | null {
    if (!initialOrder && !values.customer_id)
      return t("orders.customerRequired");
    if (!lockedItems && !hasVariants)
      return t("products.createProductVariantFirst");
    if (!lockedItems && values.items.length === 0)
      return t("orders.noProductsInCategory");
    for (const item of values.items) {
      if (!item.product_variant_id) return t("orders.selectVariant");
      if (numberValue(item.quantity) <= 0) return t("errors.required");
      if (item.unit_price === "" || numberValue(item.unit_price) < 0)
        return t("errors.required");
      const stock = inventoryByVariantId.get(item.product_variant_id);
      if (
        stock &&
        stock.stock_quantity - stock.reserved_quantity <
          numberValue(item.quantity)
      )
        return t("inventory.lowStock");
    }
    return null;
  }

  async function createQuickCustomer() {
    if (!onCreateCustomer) return;
    if (!quickCustomer.name.trim()) {
      setQuickCustomerError(t("customers.quickCreateNameRequired"));
      return;
    }
    if (!quickCustomer.phone.trim()) {
      setQuickCustomerError(t("customers.quickCreatePhoneRequired"));
      return;
    }
    try {
      setQuickCustomerError(null);
      const created = await onCreateCustomer({
        name: quickCustomer.name.trim(),
        phone: quickCustomer.phone.trim() || null,
        instagram_username: quickCustomer.instagram_username.trim() || null,
        city: null,
        region: null,
      });
      setValues((current) => ({ ...current, customer_id: created.id }));
      setCustomerSearch(created.name);
      setQuickCustomer({ name: "", phone: "", instagram_username: "" });
      setIsQuickCreateOpen(false);
    } catch {
      setQuickCustomerError(t("customers.quickCreateError"));
    }
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
    if (initialOrder && !values.customer_id) delete (payload as Partial<OrderCreatePayload>).customer_id;
    if (lockedItems) delete (payload as Partial<OrderCreatePayload>).items;
    onSubmit(payload);
  }

  return (
    <form
      className="sellora-scrollbar grid max-h-[calc(100dvh-9rem)] min-w-0 gap-4 overflow-y-auto overflow-x-hidden pr-1"
      onSubmit={submit}
      noValidate
    >
      {!hasVariants && !lockedItems ? (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">
          {t("products.createProductVariantFirst")}
        </p>
      ) : null}
      {lockedItems ? (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">
          {t("orders.archiveUnavailable")}
        </p>
      ) : null}
      <section className="grid min-w-0 gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-white/10 dark:bg-white/[0.04]">
        <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="font-bold text-slate-950 dark:text-white">
              {t("orders.customerSelector")}
            </h3>
            <p className="text-sm text-slate-500 dark:text-slate-300">
              {t("orders.customerSelectorHelp")}
            </p>
          </div>
          {onCreateCustomer ? (
            <button
              className="min-h-11 rounded-lg border border-slate-300 px-4 py-2 text-sm font-bold dark:border-white/10"
              type="button"
              onClick={() => setIsQuickCreateOpen((value) => !value)}
            >
              {t("orders.createCustomer")}
            </button>
          ) : null}
        </div>
        <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">
          {t("orders.customerSearchLabel")}
          <input
            className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2 dark:border-white/10 dark:bg-white/10 dark:text-white"
            placeholder={t("orders.customerSearchPlaceholder")}
            value={customerSearch}
            onChange={(event) => setCustomerSearch(event.target.value)}
          />
        </label>
        <div className="grid max-h-52 gap-2 overflow-y-auto rounded-lg border border-slate-200 bg-white p-2 dark:border-white/10 dark:bg-slate-950">
          {filteredCustomers.length ? (
            filteredCustomers.map((customer) => (
              <button
                className={`rounded-lg px-3 py-2 text-left text-sm ${values.customer_id === customer.id ? "bg-blue-50 text-blue-700 dark:bg-blue-500/20 dark:text-blue-100" : "hover:bg-slate-50 dark:hover:bg-white/10"}`}
                key={customer.id}
                type="button"
                onClick={() => {
                  setValues({ ...values, customer_id: customer.id });
                  setCustomerSearch(customer.name);
                }}
              >
                <strong className="block">{customer.name}</strong>
                <span className="block text-xs text-slate-500 dark:text-slate-300">
                  {[
                    customer.phone,
                    customer.instagram_username
                      ? `@${customer.instagram_username.replace(/^@/, "")}`
                      : null,
                    customer.total_orders
                      ? t("orders.customerOrdersCount", {
                          count: customer.total_orders,
                        })
                      : null,
                  ]
                    .filter(Boolean)
                    .join(" · ") || t("common.none")}
                </span>
              </button>
            ))
          ) : (
            <p className="px-3 py-2 text-sm text-slate-500 dark:text-slate-300">
              {t("orders.customerSearchEmpty")}
            </p>
          )}
        </div>
        {selectedCustomer ? (
          <div className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-100">
            <span className="font-bold">
              {t("orders.customerPreview")}: {selectedCustomer.name}
            </span>
            <span className="mt-1 block">
              {[
                selectedCustomer.phone,
                selectedCustomer.instagram_username
                  ? `@${selectedCustomer.instagram_username.replace(/^@/, "")}`
                  : null,
              ]
                .filter(Boolean)
                .join(" · ")}
            </span>
          </div>
        ) : (
          <p className="rounded-lg bg-amber-50 p-3 text-sm font-semibold text-amber-800 dark:bg-amber-500/15 dark:text-amber-100">
            {initialOrder
              ? t("orders.customerMissing")
              : t("orders.customerRequired")}
          </p>
        )}
        {isQuickCreateOpen ? (
          <div className="grid gap-3 rounded-xl border border-slate-200 bg-white p-3 dark:border-white/10 dark:bg-slate-950">
            <h4 className="font-bold text-slate-950 dark:text-white">
              {t("customers.quickCreate")}
            </h4>
            <div className="grid gap-3 sm:grid-cols-3">
              <input
                className="min-h-11 rounded-lg border border-slate-300 px-3 dark:border-white/10 dark:bg-white/10 dark:text-white"
                placeholder={t("customers.name")}
                value={quickCustomer.name}
                onChange={(event) =>
                  setQuickCustomer((current) => ({
                    ...current,
                    name: event.target.value,
                  }))
                }
              />
              <input
                className="min-h-11 rounded-lg border border-slate-300 px-3 dark:border-white/10 dark:bg-white/10 dark:text-white"
                placeholder={t("customers.phone")}
                value={quickCustomer.phone}
                onChange={(event) =>
                  setQuickCustomer((current) => ({
                    ...current,
                    phone: event.target.value,
                  }))
                }
              />
              <input
                className="min-h-11 rounded-lg border border-slate-300 px-3 dark:border-white/10 dark:bg-white/10 dark:text-white"
                placeholder={t("customers.instagram")}
                value={quickCustomer.instagram_username}
                onChange={(event) =>
                  setQuickCustomer((current) => ({
                    ...current,
                    instagram_username: event.target.value,
                  }))
                }
              />
            </div>
            {quickCustomerError ? (
              <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700 dark:bg-amber-500/15 dark:text-amber-100">
                {quickCustomerError}
              </p>
            ) : null}
            <button
              className="min-h-11 rounded-lg bg-blue-600 px-4 py-2 font-bold text-white disabled:opacity-60"
              disabled={isCreatingCustomer}
              type="button"
              onClick={() => void createQuickCustomer()}
            >
              {isCreatingCustomer
                ? t("common.loading")
                : t("customers.quickCreate")}
            </button>
          </div>
        ) : null}
      </section>
      <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">
        {t("tables.payment")}
        <select
          className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2"
          value={values.payment_status}
          onChange={(event) =>
            setValues({
              ...values,
              payment_status: event.target
                .value as OrderFormValues["payment_status"],
            })
          }
        >
          {(["PENDING", "PAID", "COD", "REFUNDED"] as const).map((status) => (
            <option key={status} value={status}>
              {formatStatus("payment", status)}
            </option>
          ))}
        </select>
      </label>

      <section className="grid min-w-0 gap-3">
        <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="font-bold text-slate-950 dark:text-white">
              {t("orders.items")}
            </h3>
            <p className="text-sm text-slate-500 dark:text-slate-300">
              {t("products.variantsDescription")}
            </p>
          </div>
          <button
            className="min-h-11 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold dark:border-white/10"
            type="button"
            disabled={!canEditItems}
            onClick={addItem}
          >
            {t("actions.addItem")}
          </button>
        </div>
        {values.items.map((item, index) => {
          const lineTotal =
            numberValue(item.quantity) * numberValue(item.unit_price);
          const filter = itemFilter(index, item);
          const filteredProducts = products.filter(
            (product) =>
              categoryMatches(product.category, filter.category) &&
              productSearchMatches(product, filter.productSearch),
          );
          const visibleProductOptions = filteredProducts.slice(
            0,
            MAX_PRODUCT_SELECTOR_OPTIONS,
          );
          const hasMoreProductOptions =
            filteredProducts.length > visibleProductOptions.length;
          const variantOptions = variants.filter((variant) => {
            const product = productById.get(variant.product_id);
            if (filter.productId)
              return variant.product_id === filter.productId;
            return product
              ? categoryMatches(product.category, filter.category)
              : filter.category === "all";
          });
          return (
            <article
              className="grid min-w-0 gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-white/10 dark:bg-white/[0.04]"
              key={index}
            >
              <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <h4 className="font-semibold text-slate-950 dark:text-white">
                  {t("orders.item")} {index + 1}
                </h4>
                <button
                  className="rounded-lg border border-rose-200 px-3 py-2 text-sm font-semibold text-rose-700 disabled:cursor-not-allowed disabled:opacity-50 dark:border-rose-400/40 dark:text-rose-200"
                  disabled={values.items.length === 1 || !canEditItems}
                  type="button"
                  onClick={() => removeItem(index)}
                >
                  {t("actions.removeItem")}
                </button>
              </div>
              <div className="grid min-w-0 gap-3 md:grid-cols-3">
                <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">
                  {t("orders.selectCategory")}
                  <select
                    className="min-h-11 w-full min-w-0 rounded-md border border-slate-300 px-3 py-2"
                    value={filter.category}
                    disabled={!canEditItems}
                    onChange={(event) =>
                      selectCategory(
                        index,
                        event.target.value as CategoryFilter,
                      )
                    }
                  >
                    <option value="all">{t("categories.allCategories")}</option>
                    {categoryOptions.map((category) => (
                      <option key={category.value} value={category.value}>
                        {category.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">
                  {t("orders.searchProduct")}
                  <input
                    className="min-h-11 w-full min-w-0 rounded-md border border-slate-300 px-3 py-2"
                    value={filter.productSearch}
                    disabled={!canEditItems}
                    placeholder={t("orders.searchProduct")}
                    onChange={(event) =>
                      setFilter(index, { productSearch: event.target.value })
                    }
                  />
                </label>
                <div className="grid min-w-0 gap-2 md:col-span-1">
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                    {t("orders.selectProduct")}
                  </span>
                  <div className="product-selector-combobox sellora-scrollbar grid max-h-64 min-w-0 gap-1 overflow-y-auto rounded-xl border border-slate-200 bg-white p-1.5 dark:border-white/10 dark:bg-slate-950">
                    {filteredProducts.length ? (
                      visibleProductOptions.map((product) => {
                        const image = productImage(product);
                        const isSelected = filter.productId === product.id;
                        return (
                          <button
                            className={`product-select-item flex min-w-0 items-center gap-2 rounded-lg border px-2 py-1.5 text-left transition ${isSelected ? "border-blue-600 bg-blue-50 dark:bg-blue-500/10" : "border-transparent hover:border-blue-200 hover:bg-slate-50 dark:border-transparent dark:hover:border-blue-300/40 dark:hover:bg-white/5"}`}
                            disabled={!canEditItems}
                            key={product.id}
                            type="button"
                            onClick={() => selectProduct(index, product.id)}
                          >
                            {image ? (
                              <img
                                className="h-9 w-9 shrink-0 rounded-lg object-cover"
                                src={image.image_url}
                                alt={image.alt_text ?? product.name}
                              />
                            ) : (
                              <span className="product-option-placeholder flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-[9px] font-black uppercase text-slate-400 dark:bg-white/10">
                                {t("orders.productOption.noImage")}
                              </span>
                            )}
                            <span className="min-w-0 flex-1">
                              <strong className="block truncate text-sm leading-5 text-slate-950 dark:text-white">
                                {product.name}
                              </strong>
                              <span className="block truncate text-[11px] leading-4 text-slate-500 dark:text-slate-300">
                                {productSummary(product)}
                              </span>
                            </span>
                          </button>
                        );
                      })
                    ) : (
                      <p className="p-3 text-sm text-slate-500 dark:text-slate-300">
                        {t("orders.productOption.noProducts")}
                      </p>
                    )}
                    {hasMoreProductOptions ? (
                      <p className="px-2 py-1 text-xs font-semibold text-slate-500 dark:text-slate-300">
                        {t("orders.productOption.refineSearch")}
                      </p>
                    ) : null}
                  </div>
                </div>
              </div>
              <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">
                {t("orders.selectVariant")}
                <select
                  className="min-h-11 w-full min-w-0 rounded-md border border-slate-300 px-3 py-2"
                  value={item.product_variant_id}
                  disabled={
                    !hasVariants || !canEditItems || variantOptions.length === 0
                  }
                  onChange={(event) => selectVariant(index, event.target.value)}
                >
                  <option value="">
                    {variantOptions.length
                      ? t("orders.selectVariant")
                      : t("orders.noVariantsForProduct")}
                  </option>
                  {variantOptions.map((variant) => (
                    <option key={variant.id} value={variant.id}>
                      {variantLabel(variant)}
                    </option>
                  ))}
                </select>
              </label>
              <div className="grid min-w-0 gap-3 sm:grid-cols-4">
                <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">
                  {t("orders.quantity")}
                  <input
                    className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2"
                    min={1}
                    type="number"
                    disabled={!canEditItems}
                    value={item.quantity}
                    onChange={(event) =>
                      updateItem(index, { quantity: event.target.value })
                    }
                  />
                </label>
                <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">
                  {t("orders.unitPrice")}
                  <input
                    className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2"
                    inputMode="decimal"
                    placeholder={t("orders.unitPrice")}
                    disabled={!canEditItems}
                    value={item.unit_price}
                    onChange={(event) =>
                      updateItem(index, { unit_price: event.target.value })
                    }
                  />
                </label>
                <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">
                  {t("orders.unitCost")}
                  <input
                    className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2"
                    inputMode="decimal"
                    placeholder={t("orders.unitCost")}
                    disabled={!canEditItems}
                    value={item.unit_cost}
                    onChange={(event) =>
                      updateItem(index, { unit_cost: event.target.value })
                    }
                  />
                </label>
                <div className="rounded-lg bg-white px-3 py-2 text-sm dark:bg-white/[0.05]">
                  <span className="text-slate-500 dark:text-slate-300">
                    {t("orders.lineTotal")}
                  </span>
                  <strong className="block text-base text-slate-950 dark:text-white">
                    {formatMoney(lineTotal, currencyCode)}
                  </strong>
                </div>
              </div>
            </article>
          );
        })}
      </section>

      <div className="grid gap-3 sm:grid-cols-4">
        <input
          className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2"
          inputMode="decimal"
          placeholder={t("orders.adCost")}
          value={values.ad_cost ?? ""}
          onChange={(event) =>
            setValues({ ...values, ad_cost: event.target.value })
          }
        />
        <input
          className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2"
          inputMode="decimal"
          placeholder={t("orders.shipping")}
          value={values.shipping_cost ?? ""}
          onChange={(event) =>
            setValues({ ...values, shipping_cost: event.target.value })
          }
        />
        <input
          className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2"
          inputMode="decimal"
          placeholder={t("orders.codFee")}
          value={values.cod_fee ?? ""}
          onChange={(event) =>
            setValues({ ...values, cod_fee: event.target.value })
          }
        />
        <input
          className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2"
          inputMode="decimal"
          placeholder={t("orders.other")}
          value={values.other_cost ?? ""}
          onChange={(event) =>
            setValues({ ...values, other_cost: event.target.value })
          }
        />
      </div>
      <textarea
        className="min-h-24 min-w-0 rounded-md border border-slate-300 px-3 py-2"
        placeholder={t("orders.notes")}
        value={values.notes ?? ""}
        onChange={(event) =>
          setValues({ ...values, notes: event.target.value })
        }
      />

      <section className="grid min-w-0 gap-2 rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-slate-700 dark:border-white/10 dark:bg-white/[0.05] dark:text-slate-200 sm:grid-cols-2">
        <span>{t("orders.itemsSubtotal")}</span>
        <strong className="text-slate-950 dark:text-white">
          {formatMoney(itemSubtotal, currencyCode)}
        </strong>
        {showProfit ? (
          <>
            <span>{t("orders.productCost")}</span>
            <strong className="text-slate-950 dark:text-white">
              {formatMoney(productCost, currencyCode)}
            </strong>
          </>
        ) : null}
        <span>{t("orders.adCost")}</span>
        <strong className="text-slate-950 dark:text-white">
          {formatMoney(adCost, currencyCode)}
        </strong>
        <span>{t("orders.shippingCodOther")}</span>
        <strong className="text-slate-950 dark:text-white">
          {formatMoney(shippingCost + codFee + otherCost, currencyCode)}
        </strong>
        {showProfit ? (
          <>
            <span>{t("orders.estimatedProfit")}</span>
            <strong className="text-emerald-700 dark:text-emerald-200">
              {formatMoney(estimatedProfit, currencyCode)}
            </strong>
          </>
        ) : null}
      </section>
      {validationError ? (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">
          {validationError}
        </p>
      ) : null}
      <button
        className="min-h-11 rounded-md bg-blue-600 px-4 py-2 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
        disabled={!lockedItems && !hasVariants}
        type="submit"
      >
        {submitLabel}
      </button>
    </form>
  );
}
// Regression compatibility markers: Create a product variant first before creating an order.; Add item; Remove item; Price is auto-filled from the selected variant and can be adjusted for discounts.; Line total; Items are locked because this order has already entered shipment workflow.
// Regression compatibility markers: Items subtotal; Estimated profit.
