"use client";

import Link from "next/link";

import type { DirectOrderEvidence } from "@/types/direct";

const REVIEW_LABELS: Record<string, string> = {
  SHIPMENT_NOT_IN_CRM: "Відправлення ще не знайдено в CRM",
  MULTIPLE_SHIPMENT_MATCHES: "ТТН збігається з кількома відправленнями",
  CUSTOMER_MISMATCH: "Клієнт у відправленні не збігається",
};

const ORDER_STATUSES: Record<string, string> = {
  NEW: "Нове",
  CONFIRMED: "Підтверджене",
  SHIPPED: "Відправлене",
  DELIVERED: "Доставлене",
  COMPLETED: "Завершене",
  RETURNED: "Повернення",
  CANCELLED: "Скасоване",
};
const PAYMENT_STATUSES: Record<string, string> = {
  PAID: "Оплачено за записом CRM",
  PENDING: "Очікує оплати",
  COD: "Накладений платіж",
  REFUNDED: "Повернено",
};

type Props = {
  evidence?: DirectOrderEvidence;
  loading: boolean;
  error: boolean;
  canManage: boolean;
  confirming: boolean;
  confirmError: boolean;
  onConfirm: () => void;
};

export function DirectOrderEvidenceCard({ evidence, loading, error, canManage, confirming, confirmError, onConfirm }: Props) {
  if (loading) {
    return <p className="border-b border-border-subtle px-4 py-3 text-xs text-text-muted" role="status">Перевіряємо ТТН із переписки…</p>;
  }
  if (error) {
    return <p className="border-b border-border-subtle px-4 py-3 text-xs text-amber-700" role="status">Зв’язок із відправленнями зараз не перевірено. Це не означає, що продажу не було.</p>;
  }
  if (!evidence || (!evidence.verified_orders.length && !evidence.needs_review.length && !evidence.scan_truncated)) {
    return null;
  }
  return (
    <section className="shrink-0 border-b border-border-subtle bg-surface-2/60 px-4 py-3" aria-label="Історія замовлень за ТТН" data-direct-order-evidence>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-black text-text-primary">Відправлення з переписки</p>
        <span className="text-xs font-semibold text-text-muted">Зіставлення за точним номером ТТН</span>
      </div>
      {evidence.verified_orders.length ? (
        <div className="space-y-2">
          {evidence.verified_orders.map((item) => (
            <div key={item.shipment_id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border-subtle bg-surface-1 px-3 py-2">
              <div className="min-w-0">
                <p className="text-sm font-bold text-text-primary">Замовлення №{item.order_number}</p>
                <p className="text-xs text-text-muted">Нова пошта: {item.tracking_masked} · {item.is_historical ? "Історичне" : "Поточне"}</p>
                <p className="text-[11px] font-semibold text-primary">{item.confirmed_in_crm ? "Зв’язок із Direct підтверджено" : "Збіг підтверджено за ТТН — зв’язок ще не збережено"}</p>
                <p className="text-[11px] text-text-muted">За даними CRM: {ORDER_STATUSES[item.order_status] ?? item.order_status} · {PAYMENT_STATUSES[item.payment_status] ?? item.payment_status}</p>
              </div>
              <Link
                href={`/orders?order_id=${encodeURIComponent(item.order_id)}`}
                className="inline-flex min-h-10 items-center rounded-xl border border-border-subtle px-3 text-xs font-bold text-primary hover:bg-surface-hover"
              >Переглянути</Link>
            </div>
          ))}
        </div>
      ) : null}
      {canManage && !evidence.scan_truncated && evidence.verified_orders.some((item) => !item.confirmed_in_crm) ? (
        <button
          type="button"
          onClick={onConfirm}
          disabled={confirming}
          className="mt-2 min-h-10 rounded-xl bg-primary px-4 py-2 text-xs font-black text-primary-foreground disabled:opacity-50"
        >
          {confirming ? "Зберігаємо…" : "Підтвердити зв’язки з існуючими замовленнями"}
        </button>
      ) : null}
      {confirmError ? <p role="alert" className="mt-2 text-xs text-rose-600">Не вдалося зберегти зв’язки. Перевірте, чи ТТН або замовлення не змінилися.</p> : null}
      {evidence.has_multiple_orders ? <p className="mt-2 text-xs font-semibold text-text-secondary">У цьому діалозі знайдено кілька окремих замовлень.</p> : null}
      {evidence.needs_review.length ? (
        <div className="mt-2 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3">
          <p className="text-xs font-bold text-amber-700">ТТН знайдено — потрібна перевірка ({evidence.needs_review.length})</p>
          <ul className="mt-1 space-y-1 text-xs text-text-secondary">
            {evidence.needs_review.map((item) => (
              <li key={`${item.source_message_id}:${item.tracking_masked}`}>
                {item.tracking_masked}: {REVIEW_LABELS[item.reason] ?? "Потрібна перевірка"}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {evidence.scan_truncated ? (
        <p className="mt-2 text-xs font-semibold text-amber-700">У цьому діалозі дуже багато ТТН. Показана лише частина — перелік не повний.</p>
      ) : null}
      <p className="mt-2 text-[11px] text-text-muted">Збіг ТТН підтверджує запис відправлення в CRM, але не доводить оплату або вручення перевізником.</p>
    </section>
  );
}