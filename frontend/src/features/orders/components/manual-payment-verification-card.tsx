"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import { ApiError, safeApiErrorMessage } from "@/services/api";
import {
  confirmManualOrderPayment, getManualPaymentVerification,
  type ManualPaymentMethod,
  type ManualPaymentVerification,
} from "@/services/manual-payment-verification";
import type { Order } from "@/types/orders";

const copy = {
  uk: {
    title: "Ручне підтвердження оплати",
    subtitle: "Без інтеграції з банком. Менеджер самостійно звіряє квитанцію та фактичне надходження.",
    warning: "Sellora не перевіряє банківський рахунок автоматично. Підтверджуйте лише після перевірки в monobank.",
    reference: "Номер операції в банку",
    referenceHint: "Унікальний ID транзакції з історії платежів; не вводьте номер картки або IBAN.",
    receipt: "Я перевірив(ла) квитанцію покупця в Direct",
    funds: "Я перевірив(ла), що гроші фактично надійшли на рахунок ФОП",
    method: "Спосіб оплати",
    amount: "Сума замовлення",
    receiptNote: "Примітка до квитанції (необов'язково)",
    receiptNotePlaceholder: "Наприклад, квитанція в Instagram Direct",
    button: "Підтвердити отримання оплати",
    loading: "Збереження…",
    verified: "Вручну підтверджено",
    verifiedBy: "Дата перевірки",
    account: "Операція",
    verifiedHint: "Це перевірка співробітника, не автоматичне підтвердження API банку.",
    unverifiedPaid: "Замовлення вже має статус «Оплачено», але окремого запису подвійної ручної перевірки немає.",
    skipped: "Для історичних, повернутих, скасованих і COD-замовлень цей сценарій не застосовується.",
    methodLabels: { BANK_IBAN: "IBAN ФОП", FOP_CARD: "Картка ФОП", MONO_ACQUIRING_LINK: "Платіжне посилання mono" },
    errors: {
      ORDER_NOT_FOUND: "Замовлення не знайдено.",
      RECEIPT_AND_BANK_CONFIRMATION_REQUIRED: "Потрібно підтвердити і квитанцію, і надходження коштів.",
      ORDER_PAYMENT_ALREADY_CONFIRMED: "Оплату цього замовлення вже підтверджено.",
      BANK_TRANSACTION_ALREADY_ASSIGNED: "Цю банківську операцію вже прив'язано до іншого замовлення.",
      ORDER_NOT_ELIGIBLE: "Це замовлення не підлягає ручному підтвердженню.",
      ORDER_NOT_PENDING_PAYMENT: "Замовлення вже не очікує оплати.",
      ORDER_CUSTOMER_OR_ITEMS_MISSING: "Спочатку додайте клієнта і товари.",
      ORDER_AMOUNT_NOT_POSITIVE: "У замовленні немає коректної суми.",
      PAYMENT_AMOUNT_MISMATCH: "Сума надходження не збігається із сумою замовлення.",
      BANK_TRANSACTION_OR_ORDER_ALREADY_CONFIRMED: "Операцію вже використано; оновіть сторінку.",
      ONLY_UAH_WORKSPACES_SUPPORTED: "Підтвердження mono доступне лише для робочих просторів із валютою UAH.",
      ORDER_NOT_PENDING_OR_PAID: "Цей статус оплати не допускає ручного підтвердження.",
    },
  },
  en: {
    title: "Manual payment verification",
    subtitle: "No bank connection. A manager reviews the receipt and real account credit.",
    warning: "Sellora cannot verify the bank account automatically. Confirm only after checking monobank.",
    reference: "Bank transaction reference",
    referenceHint: "Unique transaction ID from the banking app, not a card number or IBAN.",
    receipt: "I verified the buyer's receipt in Direct",
    funds: "I verified the funds actually reached the business account",
    method: "Payment method",
    amount: "Order amount",
    receiptNote: "Receipt note (optional)",
    receiptNotePlaceholder: "For example: customer receipt in Direct",
    button: "Confirm received payment",
    loading: "Saving…",
    verified: "Manually verified",
    verifiedBy: "Checked at",
    account: "Transaction",
    verifiedHint: "This is staff attestation, not bank API verification.",
    unverifiedPaid: "This order is paid, but there is no separate record of the two manual checks.",
    skipped: "This action is not available for historical, cancelled, returned or COD orders.",
    methodLabels: { BANK_IBAN: "FOP IBAN", FOP_CARD: "Business card", MONO_ACQUIRING_LINK: "mono payment link" },
    errors: {
      ORDER_NOT_FOUND: "Order not found.",
      RECEIPT_AND_BANK_CONFIRMATION_REQUIRED: "Both checks are required.",
      ORDER_PAYMENT_ALREADY_CONFIRMED: "Payment already verified.",
      BANK_TRANSACTION_ALREADY_ASSIGNED: "Transaction already assigned to another order.",
      ORDER_NOT_ELIGIBLE: "Order is not eligible.",
      ORDER_NOT_PENDING_PAYMENT: "Order is no longer awaiting payment.",
      ORDER_CUSTOMER_OR_ITEMS_MISSING: "Add a customer and items first.",
      ORDER_AMOUNT_NOT_POSITIVE: "Order amount is invalid.",
      PAYMENT_AMOUNT_MISMATCH: "Amount does not match the order.",
      BANK_TRANSACTION_OR_ORDER_ALREADY_CONFIRMED: "Transaction was already used. Refresh the page.",
      ONLY_UAH_WORKSPACES_SUPPORTED: "Manual mono verification is only available for UAH workspaces.",
      ORDER_NOT_PENDING_OR_PAID: "Payment status is not eligible.",
    },
  },
} as const;

function safeMoneyMinor(value: string | number): number | null {
  const text = String(value);
  if (!/^(?:0|[1-9]\d{0,11})(?:\.\d{1,2})?$/.test(text)) return null;
  const [whole, cents = ""] = text.split(".");
  const amount = Number(whole) * 100 + Number(cents.padEnd(2, "0"));
  return Number.isSafeInteger(amount) && amount > 0 ? amount : null;
}

function readableError(error: unknown, locale: "uk" | "en") {
  const labels = copy[locale].errors;
  if (error instanceof ApiError) {
    const details = error.detail;
    const key = typeof details === "string" ? details : details && typeof details === "object" && "detail" in details && typeof details.detail === "string" ? details.detail : null;
    if (key && key in labels) return labels[key as keyof typeof labels];
  }
  return safeApiErrorMessage(error);
}

export function ManualPaymentVerificationCard({
  order, workspaceId, canEdit, onPaid,
}: {
  order: Order;
  workspaceId: string;
  canEdit: boolean;
  onPaid: (verification: ManualPaymentVerification) => void;
}) {
  const { locale } = useI18n();
  const lang = locale === "en" ? "en" : "uk";
  const t = copy[lang];
  const queryClient = useQueryClient();
  const [method, setMethod] = useState<ManualPaymentMethod>("BANK_IBAN");
  const [reference, setReference] = useState("");
  const [receiptChecked, setReceiptChecked] = useState(false);
  const [fundsChecked, setFundsChecked] = useState(false);
  const [note, setNote] = useState("");
  const amountMinor = safeMoneyMinor(order.revenue);
  const query = useQuery({
    queryKey: ["order-manual-payment", workspaceId, order.id],
    queryFn: () => getManualPaymentVerification(workspaceId, order.id),
    enabled: Boolean(workspaceId && order.id && canEdit),
  });
  const mutation = useMutation({
    mutationFn: () => confirmManualOrderPayment(workspaceId, order.id, {
      payment_method: method,
      transaction_reference: reference.trim(),
      amount_minor: amountMinor ?? 0,
      receipt_checked: receiptChecked,
      bank_received_checked: fundsChecked,
      receipt_note: note.trim() || null,
    }),
    onSuccess: async (result) => {
      setReference(""); setReceiptChecked(false); setFundsChecked(false); setNote("");
      await queryClient.invalidateQueries({ queryKey: ["order-manual-payment", workspaceId, order.id] });
      onPaid(result.confirmation);
    },
  });

  if (!canEdit) return null;

  const verified = query.data;
  const eligible = !order.is_historical && ["NEW", "CONFIRMED", "SHIPPED", "DELIVERED", "COMPLETED"].includes(order.status)
    && (order.payment_status === "PENDING" || order.payment_status === "PAID") && Boolean(order.customer_id) && order.items.length > 0 && amountMinor !== null;

  return <section className="min-w-0 rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm" data-manual-payment-verification="receipt-and-bank">
    <h3 className="font-semibold">{t.title}</h3>
    <p className="mt-1 text-xs text-text-secondary">{t.subtitle}</p>
    {query.isPending ? <div className="mt-3 h-10 animate-pulse rounded-xl bg-surface-2" aria-label="Loading payment confirmation" /> : null}
    {query.isError ? <p role="alert" className="mt-2 text-sm text-danger">{safeApiErrorMessage(query.error)}</p> : null}
    {verified ? <div className="mt-3 space-y-2 rounded-xl border border-border-subtle bg-surface-2 p-3 text-sm">
      <p className="font-semibold text-success">{t.verified}</p>
      <p>{t.method}: {t.methodLabels[verified.payment_method]}</p>
      <p>{t.account}: {verified.reference_suffix}</p>
      <p>{t.amount}: {formatMoney(verified.amount_minor / 100, "UAH")}</p>
      <p>{t.verifiedBy}: {new Date(verified.verified_at).toLocaleString(lang === "uk" ? "uk-UA" : "en-US")}</p>
      <p className="text-xs text-text-muted">{t.verifiedHint}</p>
    </div> : !query.isPending && !query.isError && order.payment_status === "PAID" ? (
      <p className="mt-3 rounded-xl bg-surface-2 p-3 text-sm text-text-secondary">{t.unverifiedPaid}</p>
    ) : !query.isPending && !query.isError && eligible ? (
      <form className="mt-3 grid gap-3" onSubmit={event => { event.preventDefault(); mutation.mutate(); }}>
        {order.payment_status === "PAID" ? <p className="rounded-lg bg-surface-2 p-3 text-xs text-text-secondary">{t.unverifiedPaid}</p> : null}
        <p className="rounded-lg border border-border-subtle p-3 text-xs text-text-secondary">{t.warning}</p>
        <label className="grid gap-1 text-sm font-semibold">{t.method}
          <select className="min-h-11 rounded-xl border border-input-border bg-input-background px-3 py-2"
            value={method} onChange={event => setMethod(event.target.value as ManualPaymentMethod)}>
            {(["BANK_IBAN", "FOP_CARD", "MONO_ACQUIRING_LINK"] as const).map(value => <option key={value} value={value}>{t.methodLabels[value]}</option>)}
          </select>
        </label>
        <p className="text-sm">{t.amount}: <strong>{formatMoney(order.revenue, "UAH")}</strong></p>
        <label className="grid gap-1 text-sm font-semibold">{t.reference}
          <input className="min-h-11 rounded-xl border border-input-border bg-input-background px-3 py-2"
            value={reference} onChange={event => setReference(event.target.value)}
            minLength={6} maxLength={160} autoComplete="off" required placeholder="mono-event-..." />
          <span className="text-xs font-normal text-text-muted">{t.referenceHint}</span>
        </label>
        <label className="grid gap-1 text-sm font-semibold">{t.receiptNote}
          <input className="min-h-11 rounded-xl border border-input-border bg-input-background px-3 py-2"
            maxLength={240} value={note} onChange={event => setNote(event.target.value)} placeholder={t.receiptNotePlaceholder} />
        </label>
        <label className="flex items-start gap-2 text-sm">
          <input className="mt-1" type="checkbox" checked={receiptChecked} onChange={event => setReceiptChecked(event.target.checked)} />
          <span>{t.receipt}</span>
        </label>
        <label className="flex items-start gap-2 text-sm">
          <input className="mt-1" type="checkbox" checked={fundsChecked} onChange={event => setFundsChecked(event.target.checked)} />
          <span>{t.funds}</span>
        </label>
        <button className="min-h-11 rounded-xl bg-primary px-4 py-2 text-sm font-bold text-primary-foreground disabled:opacity-40"
          disabled={!receiptChecked || !fundsChecked || reference.trim().length < 6 || amountMinor === null || mutation.isPending}
          type="submit">{mutation.isPending ? t.loading : t.button}</button>
        {mutation.isError ? <p className="text-sm text-danger" role="alert">{readableError(mutation.error, lang)}</p> : null}
      </form>
    ) : !query.isPending && !query.isError ? (
      <p className="mt-3 text-xs text-text-muted">{t.skipped}</p>
    ) : null}
  </section>;
}
