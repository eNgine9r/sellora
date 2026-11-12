"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCheck, ChevronRight, PackageCheck, RefreshCw, Search } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useI18n } from "@/i18n/provider";
import { SmartSaleApproval, type SaleReviewDraft } from "@/features/shipments/components/smart-sale-approval";
import { getSmartSaleCandidates, type SmartSaleCandidate } from "@/services/smart-sale";
import { safeApiErrorMessage } from "@/services/api";
import {
  fetchExternalNovaPoshtaDocuments,
  scanExternalNovaPoshtaDocuments,
  type ExternalNovaPoshtaDocument,
  type ExternalNovaPoshtaScanResult,
} from "@/services/shipments";

type SaleQueueFilter = "all" | "priced" | "ready" | "unmatched";
type QueueRow = { document: ExternalNovaPoshtaDocument; candidate: SmartSaleCandidate | null };

const copy = {
  uk: {
    title: "Продажі на підтвердження",
    subtitle: "Перевірте відправлення, товар і оплату — решту збереже Sellora.",
    summary: "ТТН із кабінету Нової Пошти",
    summaryDescription: "Відправлення без оформленого замовлення Sellora. Не підтверджені продажі.",
    open: "Відкрити чергу",
    refresh: "Оновити ТТН", refreshing: "Оновлення…",
    total: "На перевірці", priced: "Є ціна з Direct", ready: "Готові", unmatched: "Без точного Direct",
    all: "Усі", priceFilter: "Є підказка ціни", readyFilter: "Готові", missingFilter: "Звірити Direct",
    search: "Пошук за ТТН або покупцем", list: "Черга відправлень",
    selected: "Вибране відправлення", select: "Оберіть відправлення",
    missingItem: "Уточнити товар", missingDirect: "Знайти переписку", readyStatus: "Перевірити продаж",
    noPrice: "Потрібна ціна", priceHint: "Є підказка ціни", provider: "Статус НП",
    noItems: "У цій черзі немає відправлень", noResults: "За фільтром нічого не знайдено",
    loading: "Завантажуємо відправлення…", scan: "Остання синхронізація",
    confirmed: "Продаж підтверджено. Замовлення створено.",
    openOrder: "Відкрити замовлення", openDirect: "Перевірити в Direct",
    standard: "Звичайне замовлення",
    back: "До списку",
  },
  en: {
    title: "Sales awaiting confirmation",
    subtitle: "Review the shipment, item and payment; Sellora records the rest.",
    summary: "TTNs from Nova Poshta account",
    summaryDescription: "Shipments without Sellora orders. Not confirmed sales.",
    open: "Open queue",
    refresh: "Sync TTNs", refreshing: "Refreshing…",
    total: "To review", priced: "Price hint", ready: "Ready", unmatched: "Unmatched Direct",
    all: "All", priceFilter: "Price hints", readyFilter: "Ready", missingFilter: "Match Direct",
    search: "Search by TTN or customer", list: "Shipment queue",
    selected: "Selected shipment", select: "Choose a shipment",
    missingItem: "Review item", missingDirect: "Find conversation", readyStatus: "Review sale",
    noPrice: "Needs price", priceHint: "Price hint found", provider: "NP status",
    noItems: "There are no pending shipments", noResults: "No shipments match these filters",
    loading: "Loading shipments…", scan: "Last sync",
    confirmed: "Sale confirmed. Order created.",
    openOrder: "Open order", openDirect: "Check in Direct",
    standard: "Standard order",
    back: "Back to queue",
  },
} as const;

function kyivDate(timestamp: number): string {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone: "Europe/Kyiv", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date(timestamp));
  const get = (type: string) => parts.find(item => item.type === type)?.value ?? "";
  return [get("year"), get("month"), get("day")].join("-");
}

function severity(row: QueueRow) {
  if (!row.candidate?.conversation_id) return "unmatched";
  if (row.candidate.state === "READY_FOR_REVIEW" && row.candidate.suggested_item) return "ready";
  return "needs-item";
}

function queueSort(a: QueueRow, b: QueueRow) {
  const priority = { ready: 0, "needs-item": 1, unmatched: 2 };
  return priority[severity(a) as keyof typeof priority] - priority[severity(b) as keyof typeof priority]
    || b.document.last_seen_at.localeCompare(a.document.last_seen_at);
}

export function NovaPoshtaExternalInbox({
  workspaceId, role, mode = "summary",
}: {
  workspaceId: string;
  role: string | undefined;
  mode?: "summary" | "full";
}) {
  const { locale } = useI18n();
  const t = locale === "en" ? copy.en : copy.uk;
  const client = useQueryClient();
  const [lastScan, setLastScan] = useState<ExternalNovaPoshtaScanResult | null>(null);
  const [activeFilter, setActiveFilter] = useState<SaleQueueFilter>("all");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, SaleReviewDraft>>({});
  const [lastConfirmed, setLastConfirmed] = useState<string | null>(null);
  const visible = role === "OWNER" || role === "MANAGER";
  const key = ["np-external-inbox", workspaceId];

  useEffect(() => {
    if (mode === "full") {
      const documentId = new URLSearchParams(window.location.search).get("document");
      if (documentId) setSelectedId(documentId);
    }
  }, [mode]);

  const query = useQuery({
    queryKey: key,
    queryFn: async () => {
      const [unmatched, conflicts] = await Promise.all([
        fetchExternalNovaPoshtaDocuments(workspaceId, "UNMATCHED"),
        fetchExternalNovaPoshtaDocuments(workspaceId, "CONFLICT"),
      ]);
      return [...conflicts, ...unmatched];
    },
    enabled: visible && mode === "full" && Boolean(workspaceId),
    staleTime: 60_000, refetchInterval: 60_000,
  });
  const sales = useQuery({
    queryKey: ["smart-sale-candidates", workspaceId],
    queryFn: () => getSmartSaleCandidates(workspaceId),
    enabled: visible && Boolean(workspaceId),
    staleTime: 60_000, refetchInterval: 60_000,
  });
  const scan = useMutation({
    mutationFn: () => scanExternalNovaPoshtaDocuments(
      workspaceId, kyivDate(Date.now()), kyivDate(Date.now()),
    ),
    onSuccess: async result => {
      setLastScan(result);
      await Promise.all([
        client.invalidateQueries({ queryKey: key }),
        client.invalidateQueries({ queryKey: ["smart-sale-candidates", workspaceId] }),
      ]);
    },
  });

  const queue = useMemo(() => {
    const byId = new Map((sales.data ?? []).map(candidate => [candidate.document_id, candidate]));
    return (query.data ?? []).map(document => ({
      document, candidate: byId.get(document.id) ?? null,
    })).sort(queueSort);
  }, [query.data, sales.data]);

  const counts = useMemo(() => ({
    total: mode === "full" ? queue.length : sales.data?.length ?? 0,
    priced: (mode === "full" ? queue.map(row => row.candidate) : sales.data ?? [])
      .filter(candidate => (candidate?.price_hints?.length ?? 0) > 0).length,
    ready: (mode === "full" ? queue.map(row => row.candidate) : sales.data ?? [])
      .filter(candidate => candidate?.state === "READY_FOR_REVIEW" && !!candidate.suggested_item).length,
    unmatched: mode === "full" ? queue.filter(row => !row.candidate?.conversation_id).length :
      (sales.data ?? []).filter(candidate => !candidate.conversation_id).length,
  }), [mode, queue, sales.data]);

  const filtered = useMemo(() => queue.filter(row => {
    const token = search.trim().toLowerCase().replace(/^@/, "");
    const matchesSearch = !token || [
      row.document.tracking_number, row.candidate?.customer_instagram,
      row.document.provider_status,
    ].some(text => text?.toLowerCase().includes(token));
    if (!matchesSearch) return false;
    if (activeFilter === "priced") return Boolean(row.candidate?.price_hints?.length);
    if (activeFilter === "ready") return severity(row) === "ready";
    if (activeFilter === "unmatched") return severity(row) === "unmatched";
    return true;
  }), [queue, search, activeFilter]);

  const selected = filtered.find(row => row.document.id === selectedId) ?? filtered[0] ?? null;
  const selectedIndex = selected ? filtered.findIndex(row => row.document.id === selected.document.id) : -1;
  const updateDraft = (documentId: string, patch: SaleReviewDraft) => {
    setDrafts(current => ({ ...current, [documentId]: { ...current[documentId], ...patch } }));
  };
  const handleConfirmed = (documentId: string, orderId: string) => {
    setLastConfirmed(orderId);
    setDrafts(current => {
      const next = { ...current };
      delete next[documentId];
      return next;
    });
    const nextCandidate = filtered[selectedIndex + 1] ?? filtered[selectedIndex - 1];
    setSelectedId(nextCandidate?.document.id ?? null);
  };

  if (!visible) return null;
  return <section id="smart-sale-inbox" className="grid min-w-0 scroll-mt-24 gap-4 rounded-2xl border border-border-subtle bg-surface p-3 sm:p-4" data-smart-sale-queue-mode={mode}>
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="min-w-0">
        <h2 className="text-base font-bold text-text-primary">{mode === "summary" ? t.summary : t.title}</h2>
        <p className="mt-1 text-xs text-text-secondary">{mode === "summary" ? t.summaryDescription : t.subtitle}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {mode === "summary" ? <Link
          href="/shipments/confirmations"
          className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary px-4 text-sm font-bold text-white transition hover:bg-primary-hover">
          {t.open} <ArrowRight aria-hidden="true" className="h-4 w-4" />
        </Link> : null}
        {role === "OWNER" ? <button type="button" disabled={scan.isPending}
          onClick={() => scan.mutate()}
          className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-input-border px-3 text-sm font-semibold text-text-primary transition hover:bg-surface-hover disabled:opacity-40">
          <RefreshCw aria-hidden="true" className={`h-4 w-4 ${scan.isPending ? "animate-spin" : ""}`} />
          {scan.isPending ? t.refreshing : t.refresh}
        </button> : null}
      </div>
    </div>
    {sales.isError || query.isError || scan.isError ? <p role="alert" className="text-sm text-red-500">
      {safeApiErrorMessage(sales.error || query.error || scan.error)}
    </p> : null}
    {lastScan ? <p role="status" className="text-xs text-text-secondary">{t.scan}: {lastScan.scanned} · {lastScan.unmatched} {t.total}</p> : null}

    <div className="grid grid-cols-2 gap-2 lg:grid-cols-4" data-sale-queue-counts>
      {([
        ["total", t.total, counts.total],
        ["priced", t.priced, counts.priced],
        ["ready", t.ready, counts.ready],
        ["unmatched", t.unmatched, counts.unmatched],
      ] as const).map(([id, label, value]) => (
        <div key={id} className="rounded-xl border border-border-subtle bg-surface-2 p-3">
          <p className="text-2xl font-bold tabular-nums text-text-primary">{sales.isLoading ? "—" : value}</p>
          <p className="mt-1 text-xs font-medium text-text-secondary">{label}</p>
        </div>
      ))}
    </div>

    {mode === "full" ? <>
      {lastConfirmed ? <div role="status" className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-3 text-sm">
        <span className="flex items-center gap-2 font-semibold text-emerald-600"><CheckCheck className="h-4 w-4" />{t.confirmed}</span>
        <Link className="text-sm font-semibold text-primary underline" href={`/orders?order_id=${encodeURIComponent(lastConfirmed)}`}>{t.openOrder}</Link>
      </div> : null}
      <div className="flex flex-wrap items-center gap-2" aria-label={t.list}>
        {([
          ["all", t.all, counts.total],
          ["priced", t.priceFilter, counts.priced],
          ["ready", t.readyFilter, counts.ready],
          ["unmatched", t.missingFilter, counts.unmatched],
        ] as const).map(([value, label, count]) => (
          <button key={value} type="button" aria-pressed={activeFilter === value}
            onClick={() => { setActiveFilter(value); setSelectedId(null); }}
            className={`min-h-10 rounded-xl border px-3 py-1.5 text-xs font-semibold transition ${activeFilter === value
              ? "border-primary bg-primary/10 text-primary" : "border-border-subtle bg-surface text-text-secondary hover:bg-surface-hover"}`}>
            {label} <span className="ml-1 tabular-nums">{count}</span>
          </button>
        ))}
      </div>
      <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(260px,0.85fr)_minmax(0,1.45fr)] lg:items-start">
        <div className="grid min-w-0 gap-2" data-smart-sale-compact-list>
          <label className="relative block">
            <Search aria-hidden="true" className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-text-muted" />
            <input type="search" aria-label={t.search} placeholder={t.search}
              value={search} onChange={e => setSearch(e.target.value)}
              className="min-h-11 w-full min-w-0 rounded-xl border border-input-border bg-input-background py-2 pl-10 pr-3 text-sm text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring" />
          </label>
          <h3 className="text-sm font-bold text-text-primary">{t.list}</h3>
          {query.isLoading || sales.isLoading ? <p className="p-3 text-sm text-text-secondary">{t.loading}</p> : null}
          {!query.isLoading && !sales.isLoading && filtered.length === 0 ? <p className="rounded-xl border border-border-subtle p-4 text-sm text-text-secondary">
            {queue.length ? t.noResults : t.noItems}
          </p> : null}
          {filtered.map(row => {
            const active = selected?.document.id === row.document.id;
            const state = severity(row);
            const label = row.candidate?.customer_instagram ? `@${row.candidate.customer_instagram.replace(/^@/, "")}` :
              `ТТН ${row.document.tracking_number.slice(-4)}`;
            return <button key={row.document.id} type="button" aria-current={active ? "true" : undefined}
              onClick={() => {
                setSelectedId(row.document.id);
                if (window.innerWidth < 1024) {
                  document.getElementById("sale-review-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
                }
              }}
              className={`flex min-h-[76px] w-full min-w-0 items-center gap-3 rounded-xl border p-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring ${active
                ? "border-primary bg-primary/10" : "border-border-subtle bg-surface hover:border-border-strong hover:bg-surface-hover"}`}
              data-smart-sale-list-row>
              <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${state === "ready" ? "bg-emerald-500/10 text-emerald-600" : state === "unmatched" ? "bg-rose-500/10 text-rose-500" : "bg-amber-500/10 text-amber-600"}`}>
                <PackageCheck aria-hidden="true" className="h-5 w-5" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-bold text-text-primary">{label}</span>
                <span className="mt-0.5 block truncate font-mono text-xs text-text-secondary">{row.document.tracking_number}</span>
                <span className="mt-0.5 block truncate text-xs text-text-secondary">
                  {state === "ready" ? t.readyStatus : state === "unmatched" ? t.missingDirect :
                    row.candidate?.price_hints?.length ? t.priceHint : t.missingItem}
                </span>
              </span>
              <ChevronRight aria-hidden="true" className="h-4 w-4 shrink-0 text-text-muted" />
            </button>;
          })}
        </div>
        <div id="sale-review-panel" className="min-w-0 scroll-mt-28 rounded-2xl border border-border-subtle bg-surface-2 p-3 sm:p-5" data-smart-sale-selected-panel>
          {selected ? <>
            <div className="mb-4 flex items-center justify-between gap-2 border-b border-border-subtle pb-3">
              <span className="text-xs font-bold uppercase tracking-wide text-text-secondary">{t.selected}</span>
              <span className="text-right text-xs text-text-secondary">{t.provider}: {selected.document.provider_status ?? "—"}</span>
            </div>
            {selected.candidate ? <SmartSaleApproval key={selected.document.id}
              workspaceId={workspaceId}
              candidate={selected.candidate}
              draft={drafts[selected.document.id] ?? {}}
              onDraftChange={patch => updateDraft(selected.document.id, patch)}
              onConfirmed={orderId => handleConfirmed(selected.document.id, orderId)}
            /> : <div className="grid gap-3">
              <h3 className="text-base font-semibold">{t.missingDirect}</h3>
              <p className="text-sm text-text-secondary">{selected.document.tracking_number}</p>
              {selected.document.direct_conversation_id ? <Link href={`/direct?conversation=${encodeURIComponent(selected.document.direct_conversation_id)}`}
                className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-border px-4 text-sm font-semibold text-primary">{t.openDirect}<ArrowRight className="h-4 w-4" /></Link> : null}
              {selected.document.direct_customer_id && !selected.document.direct_order_linked ?
                <Link href={`/orders?create=1&customer_id=${encodeURIComponent(selected.document.direct_customer_id)}`}
                  className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-border px-4 text-sm font-semibold text-primary">{t.standard}<ArrowRight className="h-4 w-4" /></Link> : null}
            </div>}
          </> : <p className="p-3 text-sm text-text-secondary">{t.select}</p>}
        </div>
      </div>
    </> : null}
  </section>;
}
