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
  ensuringCustomer, ensuringLead, leadError, onEnsureCustomer, onEnsureLead,
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

  return (
    <section className="shrink-0 rounded-2xl border border-border-subtle bg-surface-1 p-3" data-direct-sales-context>
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold text-text-muted">{t("direct.salesWorkspaceTitle")}</p>
          <p className="mt-1 flex items-center gap-2 text-sm font-bold text-text-primary" data-direct-sales-stage={stage}>
            <ShoppingBag className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
            {t("proposal.commercialStage." + stage)}
          </p>
          <p className="mt-1 break-words text-xs text-text-secondary">
            {loading ? t("direct.salesCustomerLoading") : customer?.name || t("direct.salesCustomerUnlinked")}
            {hints > 0 ? " · " + t("direct.salesCatalogHints", { count: hints }) : ""}
          </p>
          {automation?.missing_fields?.length ? (
            <p className="mt-1 text-xs font-semibold text-amber-700 dark:text-amber-200">
              {t("direct.salesMissingData")}
            </p>
          ) : null}
        </div>
        <div className="flex min-w-0 flex-wrap gap-2">
          {canManage && !customer && !loading ? (
            <button type="button" className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary px-3 py-2 text-xs font-bold text-primary-foreground disabled:opacity-50"
              disabled={ensuringCustomer} onClick={onEnsureCustomer}>
              <UserPlus className="h-4 w-4 shrink-0" />{t("direct.createProspect")}
            </button>
          ) : null}
          {canManage && orderHref ? (
            <Link className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary px-3 py-2 text-xs font-bold text-primary-foreground" href={orderHref}>
              <ShoppingBag className="h-4 w-4 shrink-0" />
              {t(automation?.linked_order_id ? "direct.createAnotherOrder" : "direct.createOrder")}
            </Link>
          ) : null}
          {existingOrderHref ? (
            <Link className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-border-subtle px-3 py-2 text-xs font-bold text-text-primary" href={existingOrderHref}>
              <CheckCircle2 className="h-4 w-4 shrink-0" />{t("direct.openOrder")}
            </Link>
          ) : null}
        </div>
      </div>
      <details className="mt-2 border-t border-border-subtle pt-2" data-direct-sales-details>
        <summary className="cursor-pointer text-xs font-semibold text-text-secondary">{t("direct.salesExpandCustomer")}</summary>
        <div className="mt-2 grid gap-2 rounded-xl bg-surface-2 p-3 text-sm">
          <p className="break-words font-semibold">
            {customer ? customer.name : t("direct.notCreated")}
            {customer?.instagram_username ? " · @" + customer.instagram_username.replace(/^@/, "") : ""}
          </p>
          {customer?.phone ? <p className="break-all text-text-secondary">{customer.phone}</p> : null}
          {conversation.linked_lead_id ? <p className="text-xs text-emerald-700">{t("direct.leadLinked")}</p> : null}
          {automation?.missing_fields?.length ? (
            <p className="text-xs text-amber-700">{t("direct.missingFields", {
              fields: automation.missing_fields.map((field) => {
                const known = ["name", "phone", "city", "delivery_address"];
                return known.includes(field) ? t("direct.salesField." + field) : t("direct.otherField");
              }).join(", "),
            })}</p>
          ) : null}
          {canManage && conversation.channel === "INSTAGRAM" && !conversation.linked_lead_id ? (
            <button className="min-h-11 w-fit rounded-xl border border-border-subtle px-3 text-xs font-semibold disabled:opacity-50"
              type="button" disabled={ensuringLead} onClick={onEnsureLead}>{t("direct.createLead")}</button>
          ) : null}
          {error || leadError ? <p className="text-xs text-rose-600" role="alert">{t("direct.customerError")}</p> : null}
        </div>
      </details>
    </section>
  );
}
