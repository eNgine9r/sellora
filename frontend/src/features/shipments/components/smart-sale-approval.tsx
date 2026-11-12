"use client";

import Image from "next/image";
import Link from "next/link";
import { useMemo, useState } from "react";
import { CheckCircle2, ExternalLink, PackageSearch, Search, ShieldCheck } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useI18n } from "@/i18n/provider";
import { fetchInventory, fetchProductVariants, fetchProducts } from "@/services/products";
import { safeApiErrorMessage } from "@/services/api";
import { confirmSmartSale, type SmartSaleCandidate } from "@/services/smart-sale";

export type SaleReviewDraft = {
  manual?: boolean;
  variantId?: string;
  search?: string;
  quantity?: string;
  price?: string;
};

const labels = {
  uk: {
    title: "Перевірка продажу", ready: "Підтвердіть продаж", needInfo: "Уточніть дані",
    approved: "Продаж зареєстровано", details: "Відкрити замовлення",
    customer: "Покупець", item: "Товар", choose: "Знайти товар за назвою або SKU",
    loading: "Завантажуємо каталог…", empty: "Товари не знайдено",
    editItem: "Змінити товар", stock: "Доступно", qty: "Кількість",
    price: "Ціна за одиницю, ₴", priceHint: "У переписці знайдено такі ціни:",
    oneQuote: "Підказка з Direct — перевірте фінальну домовленість",
    multipleQuotes: "У переписці є кілька сум — виберіть погоджену",
    note: "Ціна має бути за одиницю без доставки, а товар — саме з цієї посилки.",
    confirm: "Так, продано", checking: "Зберігаємо…",
    openDirect: "Відкрити переписку",
    bank: "Цією дією ви підтверджуєте, що особисто перевірили квитанцію, фактичне надходження коштів, товар, кількість і ціну. Банківський API не підключений.",
    needDirect: "ТТН ще не має однозначного зв'язку з Direct. Спочатку звірте переписку.",
    onlyOne: "Швидке підтвердження — для одного товару. Для кількох позицій використайте звичайне замовлення.",
    noStock: "Недостатньо доступного залишку для вибраної кількості.",
    needDetails: "Виберіть товар, кількість і перевірте ціну для підтвердження.",
    statusReason: {
      EXTERNAL_TTN_CONFLICT: "Конфлікт прив'язки ТТН",
      EXTERNAL_TTN_ALREADY_LINKED: "ТТН вже прив'язана",
      DIRECT_MATCH_AMBIGUOUS_OR_MISSING: "Немає однозначної переписки",
      DIRECT_ALREADY_HAS_ORDER: "До переписки вже прив'язане замовлення",
      PRODUCT_OR_PRICE_NEEDS_REVIEW: "Потрібно перевірити товар і ціну",
      READY_FOR_HUMAN_APPROVAL: "Потрібно підтвердити оплату й товар",
    },
  },
  en: {
    title: "Review sale", ready: "Confirm sale", needInfo: "Complete details",
    approved: "Sale recorded", details: "Open order",
    customer: "Customer", item: "Item", choose: "Find product by name or SKU",
    loading: "Loading catalog…", empty: "No matching products",
    editItem: "Change item", stock: "Available", qty: "Quantity",
    price: "Unit price, UAH", priceHint: "Prices mentioned in Direct:",
    oneQuote: "Direct suggestion — check the final agreement",
    multipleQuotes: "Multiple prices found — select the agreed amount",
    note: "Check the unit price excluding shipping and the actual item in this package.",
    confirm: "Yes, sold", checking: "Saving…",
    openDirect: "Open conversation",
    bank: "By confirming you personally attest to checking the receipt, actual bank credit, item, quantity and price. No bank API is connected.",
    needDirect: "There is no unique Direct conversation match for this TTN. Reconcile it first.",
    onlyOne: "Quick confirmation supports one item. Use standard orders for multi-item shipments.",
    noStock: "Not enough available stock for the quantity.",
    needDetails: "Choose a product, quantity and verified unit price.",
    statusReason: {
      EXTERNAL_TTN_CONFLICT: "TTN link conflict",
      EXTERNAL_TTN_ALREADY_LINKED: "TTN already linked",
      DIRECT_MATCH_AMBIGUOUS_OR_MISSING: "No unique Direct conversation",
      DIRECT_ALREADY_HAS_ORDER: "Conversation already has an order",
      PRODUCT_OR_PRICE_NEEDS_REVIEW: "Product and price need review",
      READY_FOR_HUMAN_APPROVAL: "Review payment and product",
    },
  },
} as const;

export function SmartSaleApproval({
  workspaceId, candidate, draft, onDraftChange, onConfirmed,
}: {
  workspaceId: string;
  candidate: SmartSaleCandidate;
  draft: SaleReviewDraft;
  onDraftChange: (patch: SaleReviewDraft) => void;
  onConfirmed?: (orderId: string) => void;
}) {
  const { locale } = useI18n();
  const t = locale === "en" ? labels.en : labels.uk;
  const client = useQueryClient();
  const item = candidate.suggested_item;
  const quotes = candidate.price_hints ?? [];
  const manual = draft.manual ?? !item;
  const variantId = draft.variantId ?? "";
  const quantity = draft.quantity ?? "1";
  const price = draft.price ?? item?.suggested_unit_price ?? (quotes.length === 1 ? quotes[0].unit_price : "");
  const search = draft.search ?? "";
  const [searchOpen, setSearchOpen] = useState(false);
  const [completedOrder, setCompletedOrder] = useState<string | null>(null);

  const catalog = useQuery({
    queryKey: ["smart-sale-catalog", workspaceId],
    queryFn: async () => {
      const [products, variants, inventory] = await Promise.all([
        fetchProducts(workspaceId), fetchProductVariants(workspaceId), fetchInventory(workspaceId),
      ]);
      return { products, variants, inventory };
    },
    enabled: manual && Boolean(candidate.conversation_id),
    staleTime: 60_000,
  });

  const products = useMemo(
    () => new Map((catalog.data?.products ?? []).map(product => [product.id, product])),
    [catalog.data?.products],
  );
  const stock = useMemo(
    () => new Map((catalog.data?.inventory ?? []).map(row => [
      row.product_variant_id, row.stock_quantity - row.reserved_quantity,
    ])),
    [catalog.data?.inventory],
  );
  const selected = (catalog.data?.variants ?? []).find(v => v.id === variantId);

  const choices = (catalog.data?.variants ?? [])
    .filter(v => v.is_active && v.sku &&
      (!search.trim() || [v.sku, v.color, v.size, products.get(v.product_id)?.name]
        .filter(Boolean).join(" ").toLowerCase().includes(search.trim().toLowerCase())))
    .sort((a, b) => {
      const aMatch = price && a.price && Number(a.price) === Number(price) ? 0 : 1;
      const bMatch = price && b.price && Number(b.price) === Number(price) ? 0 : 1;
      return aMatch - bMatch;
    })
    .slice(0, 16);

  const variant = manual ? selected?.id : item?.variant_id;
  const qty = manual ? Number(quantity) : item?.quantity ?? 0;
  const priceValid = /^(?:0|[1-9]\d{0,9})(?:\.\d{1,2})?$/.test(price) && Number(price) > 0;
  const stockOk = manual ? Boolean(selected) && (stock.get(selected!.id) ?? 0) >= qty
    : Boolean(item) && (item!.available_quantity ?? 0) >= qty;
  const canConfirm = Boolean(candidate.conversation_id) &&
    candidate.reason !== "EXTERNAL_TTN_CONFLICT" &&
    candidate.reason !== "EXTERNAL_TTN_ALREADY_LINKED" &&
    candidate.reason !== "DIRECT_ALREADY_HAS_ORDER" &&
    Boolean(variant) && Number.isInteger(qty) && qty > 0 && qty <= 100 &&
    priceValid && stockOk && Number(price) * qty <= 9999999999.99;

  const submit = useMutation({
    mutationFn: () => confirmSmartSale(
      workspaceId, candidate.document_id, candidate.conversation_id!,
      variant!, qty, price, manual ? "MANAGER_SELECTED" : "CATALOG_SUGGESTION",
    ),
    onSuccess: async result => {
      setCompletedOrder(result.order_id);
      await Promise.all([
        client.invalidateQueries({ queryKey: ["smart-sale-candidates", workspaceId] }),
        client.invalidateQueries({ queryKey: ["np-external-inbox", workspaceId] }),
        client.invalidateQueries({ queryKey: ["orders"] }),
        client.invalidateQueries({ queryKey: ["shipments"] }),
      ]);
      onConfirmed?.(result.order_id);
    },
  });

  const lookup = selected ? products.get(selected.product_id) : null;
  const image = lookup?.images?.find(i => i.is_primary) ?? lookup?.images?.[0];
  const displayName = lookup?.name ?? item?.product_name ?? "";

  if (completedOrder) return (
    <div role="status" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-4">
      <span className="flex items-center gap-2 text-sm font-semibold text-emerald-600"><CheckCircle2 className="h-5 w-5" />{t.approved}</span>
      <Link href={`/orders?order_id=${encodeURIComponent(completedOrder)}`} className="text-sm font-semibold text-primary underline">{t.details}</Link>
    </div>
  );

  return <div className="grid min-w-0 gap-4" data-smart-sale-review>
    <div className="min-w-0">
      <p className="text-xs font-semibold text-text-secondary">{candidate.state === "READY_FOR_REVIEW" ? t.ready : t.needInfo}</p>
      <h3 className="mt-1 text-lg font-bold text-text-primary">{t.title}</h3>
      <p className="mt-1 text-sm text-text-secondary">{candidate.customer_instagram ? `@${candidate.customer_instagram.replace(/^@/, "")}` : t.customer} · {candidate.tracking_masked}</p>
    </div>

    {!candidate.conversation_id ? <div role="status" className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-text-primary">{t.needDirect}</div> : <>
      <div className="grid gap-2">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm font-semibold">{t.item}</p>
          {!manual && item ? <button type="button" onClick={() => { onDraftChange({manual: true, variantId: "", search: "", price: ""}); setSearchOpen(true); }}
            className="text-xs font-semibold text-primary underline underline-offset-2">{t.editItem}</button> : null}
        </div>
        {!manual && item ? <div className="flex gap-3 rounded-xl border border-border-subtle bg-surface-2 p-3">
          <PackageSearch className="h-6 w-6 shrink-0 text-primary" aria-hidden="true" />
          <div className="min-w-0"><p className="truncate text-sm font-semibold">{item.product_name}</p>
            <p className="text-xs text-text-secondary">{item.sku} · {item.quantity} × {item.suggested_unit_price} ₴</p></div>
        </div> : <>
          {selected && !searchOpen ? <div className="flex items-center justify-between gap-3 rounded-xl border border-border-subtle bg-surface-2 p-2.5" data-sale-selected-product>
            <div className="flex min-w-0 items-center gap-3">
              <div className="grid h-12 w-12 shrink-0 place-items-center overflow-hidden rounded-lg bg-surface">
                {image?.image_url ? <Image unoptimized src={image.image_url} alt={image.alt_text ?? displayName} width={48} height={48} className="h-12 w-12 object-cover" /> : <PackageSearch className="h-5 w-5 text-text-muted" />}
              </div>
              <div className="min-w-0"><p className="truncate text-sm font-semibold">{displayName}</p>
                <p className="text-xs text-text-secondary">{[selected.sku, selected.color, selected.size].filter(Boolean).join(" · ")} · {t.stock}: {stock.get(selected.id) ?? 0}</p></div>
            </div>
            <button type="button" onClick={() => { onDraftChange({variantId: "", search: ""}); setSearchOpen(true); }}
              className="min-h-11 shrink-0 rounded-lg border border-border px-3 text-xs font-semibold text-primary">{t.editItem}</button>
          </div> : <div className="grid gap-2">
            <div className="relative">
              <Search aria-hidden="true" className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-text-secondary" />
              <input id={`sale-product-search-${candidate.document_id}`} type="search" autoComplete="off"
                aria-label={t.choose} placeholder={t.choose} value={search}
                onFocus={() => setSearchOpen(true)}
                onChange={event => { onDraftChange({search: event.target.value, variantId: ""}); setSearchOpen(true); }}
                className="min-h-11 w-full rounded-xl border border-input-border bg-input-background py-2 pl-10 pr-3 text-sm text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring" />
            </div>
            {catalog.isLoading ? <p className="text-sm text-text-secondary">{t.loading}</p> : null}
            {catalog.isError ? <p role="alert" className="text-sm text-red-500">{safeApiErrorMessage(catalog.error)}</p> : null}
            {catalog.isSuccess ? <div className="grid max-h-64 gap-1 overflow-y-auto rounded-xl border border-border-subtle bg-surface-2 p-1.5" data-smart-sale-product-options>
              {choices.length ? choices.map(v => {
                const product = products.get(v.product_id);
                const picture = product?.images?.find(i => i.is_primary) ?? product?.images?.[0];
                return <button key={v.id} type="button"
                  onClick={() => { onDraftChange({
                    variantId: v.id, search: "",
                    price: price || (quotes.length === 0 ? v.price ?? "" : ""),
                  }); setSearchOpen(false); }}
                  className="flex min-h-14 w-full min-w-0 items-center gap-3 rounded-lg px-2 text-left transition hover:bg-surface-hover focus-visible:ring-2 focus-visible:ring-focus-ring">
                  <div className="grid h-10 w-10 shrink-0 place-items-center overflow-hidden rounded-lg bg-surface">
                    {picture?.image_url ? <Image unoptimized src={picture.image_url} alt={picture.alt_text ?? product?.name ?? ""} width={40} height={40} className="h-10 w-10 object-cover" /> : <PackageSearch aria-hidden="true" className="h-5 w-5 text-text-muted" />}
                  </div>
                  <span className="min-w-0 flex-1"><span className="block truncate text-sm font-semibold">{product?.name ?? v.sku}</span>
                    <span className="block truncate text-xs text-text-secondary">{[v.sku, v.color, v.size].filter(Boolean).join(" · ")}</span></span>
                  <span className="shrink-0 text-right text-xs text-text-secondary">{v.price ? `${v.price} ₴` : "—"}
                    <span className="block">{t.stock}: {stock.get(v.id) ?? 0}</span></span>
                </button>;
              }) : <p className="p-3 text-sm text-text-secondary">{t.empty}</p>}
            </div> : null}
          </div>}
        </>}
        {manual ? <p className="text-xs text-text-secondary">{t.onlyOne}</p> : null}
      </div>

      {quotes.length ? <div className="rounded-xl border border-border-subtle bg-surface-2 p-3" data-smart-sale-price-hints>
        <p className="mb-2 text-xs font-semibold text-text-secondary">{t.priceHint}</p>
        <div className="flex flex-wrap gap-2">
          {quotes.map(q => <button key={q.message_id} type="button" aria-pressed={Number(price) === Number(q.unit_price)}
            onClick={() => onDraftChange({price: q.unit_price})}
            className={`min-h-10 rounded-lg border px-3 py-1.5 text-sm font-semibold ${Number(price) === Number(q.unit_price)
              ? "border-primary bg-primary/10 text-primary" : "border-border bg-surface text-text-primary hover:border-primary"}`}>{q.unit_price} ₴</button>)}
        </div>
        <p className="mt-2 text-xs text-text-secondary">{quotes.length === 1 ? t.oneQuote : t.multipleQuotes}</p>
      </div> : null}

      <div className="grid grid-cols-2 gap-3">
        {manual ? <label className="grid gap-1 text-xs font-semibold text-text-secondary">{t.qty}
          <input type="number" min={1} max={100} step={1} value={quantity}
            onChange={event => onDraftChange({quantity: event.target.value})}
            className="min-h-11 w-full rounded-xl border border-input-border bg-input-background px-3 text-sm text-text-primary" />
        </label> : <div className="grid gap-1"><span className="text-xs font-semibold text-text-secondary">{t.qty}</span><strong className="py-2 text-sm">{qty}</strong></div>}
        <label className="grid gap-1 text-xs font-semibold text-text-secondary">{t.price}
          <input type="text" inputMode="decimal" value={price}
            onChange={event => onDraftChange({price: event.target.value.replace(",", ".")})}
            className="min-h-11 min-w-0 w-full rounded-xl border border-input-border bg-input-background px-3 text-sm text-text-primary" />
        </label>
      </div>
      <p className="text-xs text-text-secondary">{t.note}</p>
    </>}

    <div className="mt-1 grid gap-3 border-t border-border-subtle pt-4">
      <p className="flex items-start gap-2 text-xs leading-relaxed text-text-secondary">
        <ShieldCheck aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
        {t.bank}
      </p>
      <button type="button" disabled={!canConfirm || submit.isPending}
        onClick={() => submit.mutate()}
        className="min-h-12 w-full rounded-xl bg-primary px-4 py-3 text-sm font-bold text-white transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-40"
        data-confirm-smart-sale>
        {submit.isPending ? t.checking : t.confirm}
      </button>
      {!canConfirm ? <p role="status" className="text-center text-xs text-text-secondary">
        {!candidate.conversation_id ? t.needDirect : !stockOk && Boolean(variant) ? t.noStock : t.needDetails}
      </p> : null}
      {candidate.conversation_id ? <Link href={`/direct?conversation=${encodeURIComponent(candidate.conversation_id)}`}
        className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-border-subtle px-4 text-sm font-semibold text-primary hover:bg-surface-hover">
        {t.openDirect}<ExternalLink aria-hidden="true" className="h-4 w-4" />
      </Link> : null}
      {submit.isError ? <p role="alert" className="text-sm text-red-500">{safeApiErrorMessage(submit.error)}</p> : null}
    </div>
  </div>;
}
