"use client";

import Link from "next/link";
import { CheckCircle2, ShoppingBag, UserPlus } from "lucide-react";
import { useI18n } from "@/i18n/provider";
import type { DirectConversation, DirectCustomerAutomationState } from "@/types/direct";
import type { DirectOrderProposal } from "@/types/order-proposal";

type Props = {
  conversation: DirectConversation;
  proposal?: DirectOrderProposal;
  automation?: DirectCustomerAutomationState;
  loading: boolean;
  error: boolean;
  canManage: boolean;
  ensuringCustomer: boolean;
  ensuringLead: boolean;
  leadError: boolean;
  onEnsureCustomer: () => void;
  onEnsureLead: () => void;
};

export function DirectSalesContext({
  conversation, proposal, automation, loading, error, canManage,
  ensuringCustomer, leadError, onEnsureCustomer,
}: Props) {
  const { t } = useI18n();
  const customer = automation?.customer;
  const stage = proposal?.commercial_stage ?? "NONE";
  const hints = proposal?.lines.filter((line) => line.candidates.length > 0).length ?? 0;
  const orderHref = customer && automation?.can_create_order
    ? "/orders?create=1&customer_id=" + encodeURIComponent(customer.id) +
      "&direct_conversation_id=" + encodeURIComponent(conversation.id)
    : null;
  const existingOrderHref = automation?.linked_order_id
    ? "/orders?order_id=" + encodeURIComponent(automation.linked_order_id)
    : null;

  const actionClass = "inline-flex min-h-10 shrink-0 items-center justify-center gap-1.5 rounded-xl bg-primary px-3 py-2 text-xs font-bold text-primary-foreground disabled:opacity-50";
  return (
    <section className="shrink-0 border-b border-border-subtle bg-surface-1/70 px-3 py-2.5 sm:px-4" data-direct-sales-context>
      <div className="flex min-w-0 flex-col items-stretch gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-3">
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-3 gap-y-1.5">
          <p className="inline-flex min-w-0 items-center gap-1.5 text-xs font-bold text-text-primary" data-direct-sales-stage={stage}>
            <ShoppingBag className="h-3.5 w-3.5 shrink-0 text-primary" aria-hidden="true" />
            <span className="truncate sm:hidden" title={t("proposal.commercialStage." + stage)}>{t("direct.salesStageShort." + stage)}</span>
            <span className="hidden truncate sm:inline">{t("proposal.commercialStage." + stage)}</span>
          </p>
          <span className="hidden h-3.5 w-px bg-border-subtle sm:block" aria-hidden="true" />
          <p className="hidden truncate text-xs text-text-secondary sm:inline">
            {loading ? t("direct.salesCustomerLoading") : customer?.name || t("direct.salesCustomerUnlinked")}
          </p>
          {hints > 0 ? <span className="hidden shrink-0 rounded-md bg-primary/10 px-1.5 py-0.5 text-[11px] font-semibold text-primary sm:inline">{t("direct.salesCatalogHints", { count: hints })}</span> : null}
        </div>
        <div className="flex shrink-0 items-center justify-end gap-2">
          {canManage && !customer && !loading ? (
            <button type="button" className={actionClass} disabled={ensuringCustomer} onClick={onEnsureCustomer}>
              <UserPlus className="h-3.5 w-3.5" aria-hidden="true" />{t("direct.createProspect")}
            </button>
          ) : canManage && orderHref ? (
            <Link className={actionClass} href={orderHref}>
              <ShoppingBag className="h-3.5 w-3.5" aria-hidden="true" />
              {t(automation?.linked_order_id ? "direct.createAnotherOrder" : "direct.createOrder")}
            </Link>
          ) : existingOrderHref ? (
            <Link className={actionClass} href={existingOrderHref}>
              <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />{t("direct.openOrder")}
            </Link>
          ) : null}
        </div>
      </div>
      {(error || leadError) ? <p role="alert" className="mt-1 text-xs text-rose-600">{t("direct.customerError")}</p> : null}
    </section>
  );
}
