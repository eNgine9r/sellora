"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useI18n } from "@/i18n/provider";
import { fetchInventory, fetchProductVariants, fetchProducts } from "@/services/products";
import { safeApiErrorMessage } from "@/services/api";
import { confirmSmartSale, type SmartSaleCandidate } from "@/services/smart-sale";

const labels = {
  uk: {
    ready: "Чи підтверджуєте продаж?",
    needInfo: "Додайте товар для реєстрації продажу",
    approved: "Продаж зареєстровано",
    price: "Фінальна ціна за одиницю, ₴",
    suggested: "Підставлена ціна з каталогу — звірте з домовленістю в Direct",
    status: "Натискаючи «Так, продано», ви підтверджуєте, що перевірили квитанцію в Direct, фактичне надходження коштів на рахунок ФОП, товар, кількість і ціну. Sellora не підключена до банку.",
    confirm: "Так, продано",
    checking: "Зберігаємо…",
    details: "Відкрити замовлення",
    openDirect: "Відкрити Direct",
    missing: "Немає однозначно визначеного товару. Оберіть його з каталогу та підтвердьте реальну ціну.",
    change: "Вибрати інший товар",
    variant: "Товар / варіант",
    search: "Пошук товару або SKU",
    choose: "Оберіть варіант",
    qty: "Кількість",
    catalogLoading: "Завантажуємо каталог…",
    customer: "Клієнт із переписки Direct",
    unsupported: "Не знайдено однозначної переписки; звірте ТТН у Direct",
    singleItem: "Це швидке оформлення підтримує один товар. Якщо в посилці кілька позицій, створіть звичайне замовлення.",
    reasons: {
      EXTERNAL_TTN_CONFLICT: "ТТН має конфлікт прив’язки",
      EXTERNAL_TTN_ALREADY_LINKED: "ТТН уже прив’язана",
      DIRECT_MATCH_AMBIGUOUS_OR_MISSING: "Не знайдено єдиної відповідної переписки Direct",
      DIRECT_ALREADY_HAS_ORDER: "Є інше замовлення у цій переписці",
      PRODUCT_OR_PRICE_NEEDS_REVIEW: "Товар і суму потрібно перевірити",
      READY_FOR_HUMAN_APPROVAL: "Перевірте товар, суму та оплату",
    },
  },
  en: {
    ready: "Confirm this sale?",
    needInfo: "Select the sold item",
    approved: "Sale recorded",
    price: "Agreed price per unit, UAH",
    suggested: "Catalog price suggested — check the agreed amount in Direct",
    status: "By clicking 'Yes, sold', you attest you checked the receipt in Direct, actual funds in your FOP bank account, item, quantity and price. Sellora has no banking connection.",
    confirm: "Yes, sold",
    checking: "Saving…",
    details: "Open order",
    openDirect: "Open Direct",
    missing: "The purchased item is not unambiguous. Select a catalog variant and verify the agreed amount.",
    change: "Select a different item",
    variant: "Item / variant",
    search: "Search products or SKU",
    choose: "Select a variant",
    qty: "Quantity",
    catalogLoading: "Loading catalog…",
    customer: "Customer from Direct conversation",
    unsupported: "No unique Direct conversation; verify the TTN in Direct",
    singleItem: "Quick confirmation supports one item only. For multi-item packages, use standard order creation.",
    reasons: {
      EXTERNAL_TTN_CONFLICT: "TTN has a linking conflict",
      EXTERNAL_TTN_ALREADY_LINKED: "TTN already linked",
      DIRECT_MATCH_AMBIGUOUS_OR_MISSING: "Unique Direct conversation not found",
      DIRECT_ALREADY_HAS_ORDER: "Conversation already has an order",
      PRODUCT_OR_PRICE_NEEDS_REVIEW: "Item and amount need verification",
      READY_FOR_HUMAN_APPROVAL: "Verify item, amount and payment",
    },
  },
} as const;

export function SmartSaleApproval({ workspaceId, candidate }: {
  workspaceId: string;
  candidate: SmartSaleCandidate;
}) {
  const { locale } = useI18n();
  const t = locale === "en" ? labels.en : labels.uk;
  const client = useQueryClient();
  const item = candidate.suggested_item;
  const [manual, setManual] = useState(!item);
  const [variantId, setVariantId] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [price, setPrice] = useState(item?.suggested_unit_price ?? "");
  const [search, setSearch] = useState("");
  const [completedOrder, setCompletedOrder] = useState<string | null>(null);
  const catalog = useQuery({
    queryKey: ["smart-sale-catalog", workspaceId],
    queryFn: async () => {
      const [products, variants, inventory] = await Promise.all([
        fetchProducts(workspaceId), fetchProductVariants(workspaceId), fetchInventory(workspaceId),
      ]);
      return { products, variants, inventory };
    },
    enabled: manual && !!candidate.conversation_id,
    staleTime: 60_000,
  });
  const productNames = useMemo(
    () => new Map((catalog.data?.products ?? []).map(product => [product.id, product.name])),
    [catalog.data?.products],
  );
  const stock = useMemo(
    () => new Map((catalog.data?.inventory ?? []).map(row => [
      row.product_variant_id, row.stock_quantity - row.reserved_quantity,
    ])),
    [catalog.data?.inventory],
  );
  const variantOptions = (catalog.data?.variants ?? [])
    .filter(v => v.is_active && v.sku &&
      (!search.trim() || [v.sku, v.color, v.size, productNames.get(v.product_id)]
        .filter(Boolean).join(" ").toLowerCase().includes(search.toLowerCase().trim())))
    .slice(0, 50);
  const selected = (catalog.data?.variants ?? []).find(v => v.id === variantId);
  const effectiveVariant = manual ? selected?.id : item?.variant_id;
  const effectiveQuantity = manual ? Number(quantity) : item?.quantity ?? 0;
  const safePrice = /^(?:0|[1-9]\d{0,9})(?:\.\d{1,2})?$/.test(price) && Number(price) > 0;
  const enoughStock = manual ? !!selected && (stock.get(selected.id) ?? 0) >= effectiveQuantity
    : !!item && (item.available_quantity ?? 0) >= effectiveQuantity;
  const canConfirm = !!candidate.conversation_id && candidate.reason !== "EXTERNAL_TTN_CONFLICT" &&
    candidate.reason !== "EXTERNAL_TTN_ALREADY_LINKED" &&
    !!effectiveVariant && Number.isInteger(effectiveQuantity) && effectiveQuantity > 0 && effectiveQuantity <= 100 &&
    safePrice && enoughStock && Number(price) * effectiveQuantity <= 9999999999.99;

  const submit = useMutation({
    mutationFn: () => confirmSmartSale(
      workspaceId, candidate.document_id, candidate.conversation_id!,
      effectiveVariant!, effectiveQuantity, price,
      manual ? "MANAGER_SELECTED" : "CATALOG_SUGGESTION",
    ),
    onSuccess: async (result) => {
      setCompletedOrder(result.order_id);
      await Promise.all([
        client.invalidateQueries({ queryKey: ["smart-sale-candidates", workspaceId] }),
        client.invalidateQueries({ queryKey: ["np-external-inbox", workspaceId] }),
        client.invalidateQueries({ queryKey: ["orders"] }),
        client.invalidateQueries({ queryKey: ["shipments"] }),
      ]);
    },
  });

  if (completedOrder) return <div role="status" className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3 text-sm">
    <span className="font-semibold text-emerald-600">{t.approved}</span>
    <Link href={`/orders?order_id=${encodeURIComponent(completedOrder)}`} className="font-semibold text-primary underline">{t.details}</Link>
  </div>;

  return <div className="grid gap-3 rounded-xl border border-border bg-surface p-3">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <span className="text-sm font-semibold">{candidate.state === "READY_FOR_REVIEW" ? t.ready : t.needInfo}</span>
      <span className="font-mono text-xs text-text-muted">{candidate.tracking_masked}</span>
    </div>
    <p className="text-xs text-text-muted">{t.reasons[candidate.reason as keyof typeof t.reasons] ?? candidate.reason}</p>
    {candidate.customer_instagram ? <p className="text-sm font-semibold">@{candidate.customer_instagram.replace(/^@/, "")}</p> : null}
    {candidate.conversation_id ? <p className="text-xs text-text-muted">{t.customer}</p> : <p className="text-xs text-text-muted">{t.unsupported}</p>}
    {candidate.conversation_id && !manual && item ? <div className="grid gap-2">
      <p className="text-sm">{item.product_name} · {item.sku} · {item.quantity} шт.</p>
      <p className="text-xs text-text-muted">{t.suggested}</p>
    </div> : null}
    {candidate.conversation_id && manual ? <div className="grid gap-2">
      <p className="text-xs text-text-muted">{t.missing}</p>
      <p className="text-xs font-medium text-amber-700">{t.singleItem}</p>
      <label className="grid gap-1 text-xs font-semibold">{t.search}
        <input type="search" className="min-h-11 rounded-lg border border-input-border bg-input-background px-3 text-sm"
          value={search} onChange={e => { setSearch(e.target.value); setVariantId(""); setPrice(""); }} />
      </label>
      {catalog.isLoading ? <p className="text-xs text-text-muted">{t.catalogLoading}</p> : null}
      {catalog.isError ? <p role="alert" className="text-xs text-red-500">{safeApiErrorMessage(catalog.error)}</p> : null}
      <label className="grid gap-1 text-xs font-semibold">{t.variant}
        <select className="min-h-11 min-w-0 rounded-lg border border-input-border bg-input-background px-2 text-sm"
          value={variantId} onChange={e => {
            const id = e.target.value;
            setVariantId(id);
            const chosen = catalog.data?.variants.find(v => v.id === id);
            setPrice(chosen?.price ?? "");
          }}>
          <option value="">{t.choose}</option>
          {variantOptions.map(v => <option key={v.id} value={v.id}>
            {[productNames.get(v.product_id), v.sku, v.color, v.size, `зал. ${stock.get(v.id) ?? 0}`].filter(Boolean).join(" · ")}
          </option>)}
        </select>
      </label>
      <label className="grid gap-1 text-xs font-semibold">{t.qty}
        <input type="number" min={1} max={100} step={1} value={quantity}
          onChange={e => setQuantity(e.target.value)}
          className="min-h-11 w-24 rounded-lg border border-input-border bg-input-background px-2 text-sm" />
      </label>
    </div> : null}
    {candidate.conversation_id && !manual && item ? <button type="button"
      className="w-fit text-xs font-semibold text-primary underline underline-offset-2"
      onClick={() => { setManual(true); setPrice(""); }}>{t.change}</button> : null}
    {candidate.conversation_id ? <label className="grid gap-1 text-xs font-semibold">{t.price}
      <input type="text" inputMode="decimal" aria-label={t.price}
        value={price} onChange={event => setPrice(event.target.value)}
        className="min-h-11 w-36 rounded-lg border border-input-border bg-input-background px-3 py-2 text-sm text-text-primary" />
    </label> : null}
    {canConfirm ? <p className="rounded-lg bg-amber-500/10 p-3 text-xs text-text-muted">{t.status}</p> : null}
    <div className="flex flex-wrap gap-2">
      {canConfirm ? <button type="button" disabled={submit.isPending}
        onClick={() => submit.mutate()}
        className="min-h-11 rounded-lg bg-primary px-4 py-2 text-xs font-bold text-white disabled:opacity-40"
      >{submit.isPending ? t.checking : t.confirm}</button> : null}
      {candidate.conversation_id ? <Link href={`/direct?conversation=${encodeURIComponent(candidate.conversation_id)}`}
        className="inline-flex min-h-11 items-center rounded-lg border border-input-border px-3 text-xs font-semibold text-primary"
      >{t.openDirect}</Link> : null}
    </div>
    {submit.isError ? <p role="alert" className="text-xs text-red-500">{safeApiErrorMessage(submit.error)}</p> : null}
  </div>;
}
