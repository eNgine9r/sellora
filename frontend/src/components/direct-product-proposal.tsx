"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useI18n } from "@/i18n/provider";
import { fetchDirectProductProposal } from "@/services/direct";

export function DirectProductProposal({ workspaceId, conversationId, customerId, canCreate }: {
  workspaceId: string; conversationId: string; customerId?: string | null; canCreate: boolean;
}) {
  const { locale } = useI18n();
  const [requestedId, setRequestedId] = useState<string | null>(null);
  const ua = locale === "uk";
  const q = useQuery({ queryKey: ["direct-product-proposal", workspaceId, conversationId],
    queryFn: () => fetchDirectProductProposal(conversationId), enabled: requestedId === conversationId,
    staleTime: 0, refetchOnWindowFocus: false });
  const p = requestedId === conversationId && q.data?.conversation_id === conversationId ? q.data : undefined;
  return <section className="border-b border-border-subtle bg-surface-2/40 px-4 py-3" aria-label={ua ? "Товар із переписки" : "Product from conversation"}>
    <div className="flex flex-wrap items-center justify-between gap-2"><p className="text-sm font-black">{ua ? "Товар із переписки" : "Product from conversation"}</p>
      <button type="button" className="min-h-10 rounded-xl border border-border-subtle px-3 text-xs font-bold" onClick={() => { if (requestedId === conversationId) void q.refetch(); else setRequestedId(conversationId); }}>{ua ? "Знайти підказки" : "Find suggestions"}</button></div>
    {q.isFetching && requestedId === conversationId ? <p role="status" className="mt-2 text-xs">{ua ? "Перевіряємо доступну переписку…" : "Checking available conversation…"}</p> : null}
    {q.isError && requestedId === conversationId ? <p role="alert" className="mt-2 text-xs text-danger">{ua ? "Не вдалося отримати підказки. Спробуйте ще раз." : "Could not load suggestions. Try again."}</p> : null}
    {p ? <div className="mt-2 grid gap-2 text-xs">
      <p className="text-text-secondary">{ua ? "Це лише підказки. Перевірте переписку, варіант, ціну й кількість перед оформленням." : "Suggestions only. Check the conversation, variant, price and quantity before ordering."}</p>
      {p.catalog_truncated || p.context_truncated ? <p className="font-bold text-amber-700">{ua ? "Каталог або переписка переглянуті не повністю; підказки можуть бути неповними." : "The catalog or conversation was not fully scanned; suggestions may be incomplete."}</p> : null}
      {p.analysis_state === "STALE" ? <p className="text-amber-700">{ua ? "Збережений аналіз міг застаріти після нових повідомлень." : "Saved analysis may be stale after new messages."}</p> : null}
      {!p.lines.length ? <p>{ua ? "Не знайдено надійних підказок. Оберіть товар вручну." : "No reliable suggestions found. Select a product manually."}</p> : null}
      {p.lines.map(line => <div key={line.id} className="grid gap-2 rounded-xl border border-border-subtle bg-surface-1 p-3">
        <p className="font-bold break-words">{line.mention_text}</p>
        <p className="text-text-secondary">{line.source === "ANALYSIS_CONTEXT" ? (ua ? "Джерело: збережений аналіз, перевірте чат" : "Source: saved analysis; check the chat") : line.source === "INBOUND_SKU" ? (ua ? "Джерело: артикул у повідомленні" : "Source: SKU in message") : (ua ? "Джерело: назва або категорія в повідомленні" : "Source: name or category in message")}</p>
        {line.evidence.map(e => <blockquote key={e.message_id} className="break-words border-l-2 border-primary pl-2 text-text-secondary">{e.snippet}</blockquote>)}
        {line.match_status === "NOT_FOUND" ? <p>{ua ? "Товар у каталозі не визначено." : "No catalog product identified."}</p> : null}
        {line.candidates.map(c => <div key={c.variant_id} className="grid gap-1 rounded-lg border border-border-subtle p-2"><p className="break-words font-semibold">{[c.product_name, c.sku, c.color, c.size].filter(Boolean).join(" · ")}</p><p>{ua ? "Ціна" : "Price"}: {c.price ?? "—"} · {ua ? "Доступно" : "Available"}: {c.available_quantity ?? "—"}</p>
          {canCreate && customerId ? <Link className="w-fit min-h-10 rounded-lg border border-primary px-3 py-2 font-bold text-primary" href={`/orders?create=1&customer_id=${encodeURIComponent(customerId)}&direct_conversation_id=${encodeURIComponent(conversationId)}&variant_id=${encodeURIComponent(c.variant_id)}`}>{ua ? "Обрати для замовлення" : "Choose for order"}</Link> : null}</div>)}
        {line.candidates_truncated ? <p className="text-amber-700">{ua ? "Показано лише частину варіантів. За потреби знайдіть товар вручну." : "Only some variants are shown. Search manually if needed."}</p> : null}
      </div>)}
    </div> : null}
  </section>;
}
