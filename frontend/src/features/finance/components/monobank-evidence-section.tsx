"use client";

import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import { safeApiErrorMessage } from "@/services/api";
import { fetchBankPaymentEvidence } from "@/services/bank-payment-evidence";
import type { BankPaymentEvidence, BankPaymentKind, BankPaymentRail } from "@/types/bank-payment-evidence";

const content = {
  uk: {
    heading: "monobank · Звірка оплат",
    subtitle: "IBAN ФОП, картка ФОП і платіжні посилання — один реєстр без дублювання",
    disconnected: "Підключення до банку ще не активоване",
    guard: "Імпортовані дані — лише доказ для перевірки. Sellora не змінює оплату, дохід чи прибуток без підтвердженого платежу та однозначного замовлення.",
    empty: "Записів для перевірки поки немає. Це не означає, що оплат у банку немає.",
    limit: "Останні 50 записів",
    date: "Дата", payment: "Спосіб", amount: "Сума", reference: "Замовлення / операція", state: "Перевірка",
    reason: {
      REQUIRES_PROVIDER_AND_RECEIPT_VERIFICATION: "Потрібне підтвердження банку та квитанції",
      BANK_CREDIT_CLASSIFICATION_REQUIRED: "Уточнити походження зарахування",
      PAYOUT_NOT_CUSTOMER_PAYMENT: "Виплата еквайрингу, не другий продаж",
      REFUND_NEEDS_PAYMENT_ALLOCATION: "Повернення — потрібна звірка",
      BANK_HOLD_NOT_SETTLED: "Кошти ще в холді",
      ORDER_REFERENCE_MISSING: "Замовлення не вказано",
      ORDER_NOT_FOUND: "Замовлення не знайдено",
      HISTORICAL_ORDER_NOT_VERIFIED: "Історичне замовлення",
      ORDER_CANCELLED_OR_RETURNED: "Скасоване або повернуте замовлення",
      ORDER_PAYMENT_ALREADY_PROCESSED: "Оплату вже оброблено",
      ORDER_AMOUNT_MISMATCH: "Сума не збігається",
    },
    rail: { BANK_IBAN: "IBAN", FOP_CARD: "Картка ФОП", MONO_ACQUIRING_LINK: "Mono-посилання", UNKNOWN_ACCOUNT_TRANSFER: "Переказ на рахунок" },
    kind: { CUSTOMER_PAYMENT: "Платіж", UNCLASSIFIED_CREDIT: "Невизначене надходження", ACQUIRING_PAYOUT: "Виплата еквайрингу", REFUND: "Повернення" },
  },
  en: {
    heading: "monobank · Payment reconciliation",
    subtitle: "FOP IBAN, business card and merchant payment links in one deduplicated ledger",
    disconnected: "Bank connection is not active yet",
    guard: "Imported entries are review evidence only. Sellora does not update paid status, revenue, or profit without a verified payment and an unambiguous order.",
    empty: "No evidence records yet. This does not imply there are no bank payments.",
    limit: "Latest 50 entries",
    date: "Date", payment: "Method", amount: "Amount", reference: "Order / transaction", state: "Review",
    reason: {
      REQUIRES_PROVIDER_AND_RECEIPT_VERIFICATION: "Bank and receipt verification required",
      BANK_CREDIT_CLASSIFICATION_REQUIRED: "Classify incoming credit",
      PAYOUT_NOT_CUSTOMER_PAYMENT: "Acquiring payout, not a second sale",
      REFUND_NEEDS_PAYMENT_ALLOCATION: "Refund requires reconciliation",
      BANK_HOLD_NOT_SETTLED: "Funds still on hold",
      ORDER_REFERENCE_MISSING: "Order reference missing",
      ORDER_NOT_FOUND: "Order not found",
      HISTORICAL_ORDER_NOT_VERIFIED: "Historical order",
      ORDER_CANCELLED_OR_RETURNED: "Cancelled or returned order",
      ORDER_PAYMENT_ALREADY_PROCESSED: "Payment already processed",
      ORDER_AMOUNT_MISMATCH: "Amount mismatch",
    },
    rail: { BANK_IBAN: "IBAN", FOP_CARD: "FOP card", MONO_ACQUIRING_LINK: "Mono link", UNKNOWN_ACCOUNT_TRANSFER: "Account transfer" },
    kind: { CUSTOMER_PAYMENT: "Payment", UNCLASSIFIED_CREDIT: "Unclassified credit", ACQUIRING_PAYOUT: "Acquiring payout", REFUND: "Refund" },
  },
};

function last4(value: string) {
  return value.length > 4 ? `••••${value.slice(-4)}` : "••••";
}

export function MonobankEvidenceSection() {
  const { locale } = useI18n();
  const text = locale === "en" ? content.en : content.uk;
  const { currentWorkspace, currentWorkspaceId, status } = useAuth();
  const canManage = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";
  const ledger = useQuery({
    queryKey: ["monobank-evidence", currentWorkspaceId],
    queryFn: () => fetchBankPaymentEvidence(),
    enabled: status === "authenticated" && Boolean(currentWorkspaceId) && canManage,
  });

  if (!canManage) return null;

  return <section data-monobank-evidence="review-only-v1" className="min-w-0 rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm sm:p-5">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-lg font-bold">{text.heading}</h2>
        <p className="mt-1 text-sm text-text-secondary">{text.subtitle}</p>
      </div>
      <span className="rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 text-xs font-semibold text-text-secondary">{text.disconnected}</span>
    </div>
    <p className="mt-3 text-xs text-text-secondary">{text.guard}</p>
    {ledger.isPending ? <div className="mt-4 h-16 animate-pulse rounded-xl bg-surface-2" aria-label="Loading bank evidence" /> : null}
    {ledger.isError ? <p role="alert" className="mt-3 text-sm text-danger">{safeApiErrorMessage(ledger.error)}</p> : null}
    {ledger.data?.rows.length === 0 ? <p className="mt-4 rounded-xl border border-dashed border-border-subtle p-4 text-sm text-text-secondary">{text.empty}</p> : null}
    {ledger.data?.rows.length ? <div className="mt-4">
      <p className="mb-2 text-xs text-text-muted">{text.limit} · {ledger.data.total_count}</p>
      <div className="max-h-80 overflow-auto">
        <table className="min-w-[680px] w-full text-left text-xs">
          <thead><tr className="text-text-secondary"><th className="p-2">{text.date}</th><th className="p-2">{text.payment}</th><th className="p-2">{text.amount}</th><th className="p-2">{text.reference}</th><th className="p-2">{text.state}</th></tr></thead>
          <tbody>{ledger.data.rows.map((row: BankPaymentEvidence) => <tr key={row.id} className="border-t border-border-subtle">
            <td className="p-2 whitespace-nowrap">{row.occurred_at.slice(0, 10)}</td>
            <td className="p-2">{text.rail[row.rail as BankPaymentRail]}<span className="block text-text-muted">{text.kind[row.kind as BankPaymentKind]}</span></td>
            <td className="p-2 font-semibold whitespace-nowrap">{formatMoney(row.amount_minor / 100, "UAH")}</td>
            <td className="p-2">{row.order_number ?? "—"}<span className="block text-text-muted">{last4(row.external_reference)}</span></td>
            <td className="p-2">{text.reason[row.review_reason as keyof typeof text.reason] ?? row.review_reason}</td>
          </tr>)}</tbody>
        </table>
      </div>
    </div> : null}
  </section>;
}
