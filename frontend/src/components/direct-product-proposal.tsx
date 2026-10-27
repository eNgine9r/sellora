"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useI18n } from "@/i18n/provider";
import { fetchDirectProductProposal } from "@/services/direct";

export function DirectProductProposal({ workspaceId, conversationId, customerId, canCreate }: {
  workspaceId: string; conversationId: string; customerId?: string | null; canCreate: boolean;
}) {
  const { t } = useI18n();
  const [requestedId, setRequestedId] = useState<string | null>(null);
  const q = useQuery({ queryKey: ["direct-product-proposal", workspaceId, conversationId],
    queryFn: () => fetchDirectProductProposal(conversationId), enabled: requestedId === conversationId,
    staleTime: 0, refetchOnWindowFocus: false });
  const p = requestedId === conversationId && q.data?.conversation_id === conversationId ? q.data : undefined;
  return <section className="border-b border-border-subtle bg-surface-2/40 px-4 py-3" aria-label={t("directProductProposal.title")}>
    <div className="flex flex-wrap items-center justify-between gap-2"><p className="text-sm font-black">{t("directProductProposal.title")}</p>
      <button type="button" className="min-h-10 rounded-xl border border-border-subtle px-3 text-xs font-bold" onClick={() => { if (requestedId === conversationId) void q.refetch(); else setRequestedId(conversationId); }}>{t("directProductProposal.find")}</button></div>
    {q.isFetching && requestedId === conversationId ? <p role="status" className="mt-2 text-xs">{t("directProductProposal.loading")}</p> : null}
    {q.isError && requestedId === conversationId ? <p role="alert" className="mt-2 text-xs text-danger">{t("directProductProposal.error")}</p> : null}
    {p ? <div className="mt-2 grid gap-2 text-xs">
      <p className="text-text-secondary">{t("directProductProposal.help")}</p>
      {p.catalog_truncated || p.context_truncated ? <p className="font-bold text-amber-700">{t("directProductProposal.truncated")}</p> : null}
      {p.analysis_state === "STALE" ? <p className="text-amber-700">{t("directProductProposal.stale")}</p> : null}
      {!p.lines.length ? <p>{t("directProductProposal.empty")}</p> : null}
      {p.lines.map(line => <div key={line.id} className="grid gap-2 rounded-xl border border-border-subtle bg-surface-1 p-3">
        <p className="font-bold break-words">{line.mention_text}</p>
        <p className="text-text-secondary">{line.source === "ANALYSIS_CONTEXT" ? (t("directProductProposal.analysisSource")) : line.source === "INBOUND_SKU" ? (t("directProductProposal.skuSource")) : (t("directProductProposal.productSource"))}</p>
        {line.evidence.map(e => <blockquote key={e.message_id} className="break-words border-l-2 border-primary pl-2 text-text-secondary">{e.snippet}</blockquote>)}
        {line.match_status === "NOT_FOUND" ? <p>{t("directProductProposal.notFound")}</p> : null}
        {line.candidates.map(c => <div key={c.variant_id} className="grid gap-1 rounded-lg border border-border-subtle p-2"><p className="break-words font-semibold">{[c.product_name, c.sku, c.color, c.size].filter(Boolean).join(" · ")}</p><p>{t("directProductProposal.price")}: {c.price ?? "—"} · {t("directProductProposal.available")}: {c.available_quantity ?? "—"}</p>
          {canCreate && customerId ? <Link className="w-fit min-h-10 rounded-lg border border-primary px-3 py-2 font-bold text-primary" href={`/orders?create=1&customer_id=${encodeURIComponent(customerId)}&direct_conversation_id=${encodeURIComponent(conversationId)}&variant_id=${encodeURIComponent(c.variant_id)}`}>{t("directProductProposal.choose")}</Link> : null}</div>)}
        {line.candidates_truncated ? <p className="text-amber-700">{t("directProductProposal.more")}</p> : null}
      </div>)}
    </div> : null}
  </section>;
}
