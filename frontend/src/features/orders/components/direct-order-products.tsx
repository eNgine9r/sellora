"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import { fetchDirectOrderProposal } from "@/services/direct";
import { OrderProposalLine, ProposalItemSelection } from "@/types/order-proposal";

type Selection = { variantId: string; quantity: string; reviewedVersion: string | null; manualPrice: string };
const control = "min-h-11 min-w-0 w-full rounded-xl border border-input-border bg-input-background px-3 py-2 text-sm";
function initialSelection(line: OrderProposalLine): Selection {
  return { variantId: !line.requires_review && line.match_status === "MATCHED" ? line.candidates[0]?.variant_id ?? "" : "", quantity: String(line.quantity), reviewedVersion: null, manualPrice: "" };
}

export function DirectOrderProducts({ workspaceId, conversationId, currencyCode, onApply }: {
  workspaceId: string; conversationId: string; currencyCode: string;
  onApply: (items: ProposalItemSelection[]) => string | null;
}) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const queryKey = ["direct-order-proposal", workspaceId, conversationId];
  const [selections, setSelections] = useState<Record<string, Selection>>({});
  const [feedback, setFeedback] = useState<{ error: boolean; text: string } | null>(null);
  const query = useQuery({
    queryKey,
    queryFn: () => fetchDirectOrderProposal(workspaceId, conversationId),
    retry: false,
  });
  // Include the successful update counter: even an already-stale response with
  // structurally identical data is a new verification snapshot, not old consent.
  const snapshotVersion = () => {
    const state = queryClient.getQueryState(queryKey);
    return `${state?.dataUpdatedAt ?? 0}:${state?.dataUpdateCount ?? 0}`;
  };
  const verifiedVersion = `${query.dataUpdatedAt}:${queryClient.getQueryState(queryKey)?.dataUpdateCount ?? 0}`;
  // No effect copies results into items: only the explicit Apply action may do so.
  const proposal = query.data?.conversation_id === conversationId ? query.data : undefined;
  const selection = (line: OrderProposalLine) => selections[line.id] ?? initialSelection(line);
  const update = (line: OrderProposalLine, patch: Partial<Selection>) => {
    setSelections((current) => ({ ...current, [line.id]: { ...(current[line.id] ?? initialSelection(line)), ...patch } }));
    setFeedback(null);
  };
  const apply = () => {
    if (query.isFetching || query.isError) return;
    const items: ProposalItemSelection[] = [];
    for (const line of proposal?.lines ?? []) {
      const selected = selection(line);
      if (!selected.variantId) continue;
      const candidate = line.candidates.find((item) => item.variant_id === selected.variantId);
      const quantity = Number(selected.quantity);
      let error = "";
      if (!Number.isInteger(quantity) || quantity < 1 || quantity > 999) error = t("proposal.invalidQuantity");
      else if (line.requires_review && selected.reviewedVersion !== snapshotVersion()) error = t("proposal.reviewRequired");
      else if (!candidate) error = t("proposal.catalogChanged");
      else if (candidate.available_quantity != null && quantity > candidate.available_quantity) error = t("fulfillment.validation.stock");
      else if (candidate.price == null && (!selected.manualPrice.trim() || !Number.isFinite(Number(selected.manualPrice)) || Number(selected.manualPrice) < 0)) error = t("proposal.manualPriceRequired");
      if (error) { setFeedback({ error: true, text: error }); return; }
      items.push({ variantId: selected.variantId, quantity, unitPrice: candidate!.price == null ? selected.manualPrice : String(candidate!.price) });
    }
    if (!items.length) { setFeedback({ error: true, text: t("proposal.chooseCandidate") }); return; }
    const error = onApply(items);
    setFeedback({ error: Boolean(error), text: error ?? t("proposal.applied") });
  };
  return <section className="grid min-w-0 gap-3 rounded-2xl border border-border-subtle p-3" data-direct-order-products>
    <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-black">{t("proposal.title")}</h3><button className="min-h-10 rounded-xl border border-border-subtle px-3 text-sm font-bold" type="button" disabled={query.isFetching} onClick={() => void query.refetch()}>{t("proposal.refresh")}</button></div>
    <p className="text-xs text-text-secondary">{t("proposal.help")}</p>
    {query.isPending ? <p role="status">{t("proposal.loading")}</p> : null}
    {query.isError ? <p role="alert" className="text-sm text-danger">{t("proposal.error")}</p> : null}
    {proposal ? <>
      <p className="text-sm text-text-secondary">{t(`proposal.state.${proposal.analysis_state}`)}</p>
      {proposal.catalog_truncated ? <p className="text-sm font-semibold">{t("proposal.catalogLimit")}</p> : null}
      {proposal.context_truncated ? <p className="text-xs text-text-secondary">{t("proposal.contextLimit")}</p> : null}
      {!proposal.lines.length ? <p className="text-sm">{t("proposal.empty")}</p> : null}
      {proposal.lines.map((line) => {
        const selected = selection(line);
        const candidate = line.candidates.find((item) => item.variant_id === selected.variantId);
        return <article key={line.id} className="grid min-w-0 gap-2 rounded-xl bg-surface-2 p-3" data-proposal-line={line.id}>
          <strong className="break-words">{line.mention_text}</strong>
          <p className="text-xs text-text-secondary">{t(`proposal.source.${line.source}`)} · {t(`proposal.reason.${line.reason}`)}</p>
          {line.evidence.map((evidence) => <blockquote className="break-words text-xs text-text-secondary" key={evidence.message_id}>{evidence.snippet}</blockquote>)}
          {line.source === "ANALYSIS_CONTEXT" ? <p className="text-xs text-text-secondary">{t("proposal.contextOnly")}</p> : null}
          {line.candidates.length ? <>
            <label className="grid gap-1 text-sm font-semibold">{t("proposal.variant")}<select aria-label={t("proposal.variant")} className={control} value={selected.variantId} onChange={(event) => update(line, { variantId: event.target.value })}><option value="">{t("proposal.chooseCandidate")}</option>{line.candidates.map((item) => <option value={item.variant_id} key={item.variant_id}>{[item.product_name, item.sku, item.color, item.size].filter(Boolean).join(" · ")} · {item.price == null ? t("proposal.unknownPrice") : formatMoney(item.price, currencyCode)} · {t("orders.available")}: {item.available_quantity ?? t("proposal.unknownStock")}</option>)}</select></label>
            <label className="grid gap-1 text-sm font-semibold">{t("orders.quantity")}<input className={control} type="number" min="1" max="999" value={selected.quantity} onChange={(event) => update(line, { quantity: event.target.value })} /></label>
            {candidate?.price == null && candidate ? <label className="grid gap-1 text-sm font-semibold">{t("proposal.manualPrice")}<input className={control} type="number" min="0" step="0.01" value={selected.manualPrice} onChange={(event) => update(line, { manualPrice: event.target.value })} /></label> : null}
            {line.requires_review ? <label className="flex items-start gap-2 text-sm"><input className="mt-1" type="checkbox" checked={selected.reviewedVersion === verifiedVersion} onChange={(event) => update(line, { reviewedVersion: event.target.checked ? verifiedVersion : null })} />{t("proposal.reviewed")}</label> : null}
          </> : null}
          {line.candidates_truncated ? <p className="text-xs">{t("proposal.candidateLimit")}</p> : null}
        </article>;
      })}
      {proposal.lines.some((line) => line.candidates.length > 0) ? <button className="min-h-11 rounded-xl bg-primary px-4 font-bold text-primary-foreground" type="button" disabled={query.isFetching || query.isError} onClick={apply}>{t("proposal.apply")}</button> : null}
    </> : null}
    {feedback ? <p role={feedback.error ? "alert" : "status"} className={feedback.error ? "text-sm text-danger" : "text-sm text-text-secondary"}>{feedback.text}</p> : null}
  </section>;
}
