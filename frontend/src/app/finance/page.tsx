"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useMemo, useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { dateRangeForPreset, dateRangePresetKeys, type DateRangePreset } from "@/lib/date-range-presets";
import { formatMoney } from "@/lib/currency";
import { safeApiErrorMessage } from "@/services/api";
import { createFinanceAdjustment, deleteFinanceAdjustment, fetchFinanceAdjustments, fetchFinanceSummary, fetchFinanceTrends, updateFinanceAdjustment } from "@/services/finance";
import { useI18n } from "@/i18n/provider";
import type { FinanceAdjustment, FinanceAdjustmentCategory, FinanceAdjustmentPayload, FinanceAdjustmentType, FinanceSummary } from "@/types/finance";

const adjustmentTypes: FinanceAdjustmentType[] = ["EXPENSE", "REFUND", "DISCOUNT", "FEE", "SHIPPING_ADJUSTMENT", "CORRECTION", "OTHER"];
const adjustmentCategories: FinanceAdjustmentCategory[] = ["PACKAGING", "DELIVERY", "PAYMENT_FEE", "MARKETPLACE_FEE", "TOOLS", "SALARY", "RENT", "REFUND", "DISCOUNT", "ADJUSTMENT", "OTHER"];

const initialForm = { type: "EXPENSE" as FinanceAdjustmentType, category: "PACKAGING" as FinanceAdjustmentCategory, amount: "", occurred_at: new Date().toISOString().slice(0, 10), title: "", description: "" };

function formatPercent(value?: string | null) {
  if (value == null) return "—";
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "—";
  return `${amount.toLocaleString("uk-UA", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

function KpiCard({ label, value, helper, tone = "default" }: { label: string; value: string; helper?: string; tone?: "default" | "profit" | "warning" }) {
  const toneClasses = { default: "border-slate-100 bg-white", profit: "border-emerald-100 bg-emerald-50", warning: "border-amber-100 bg-amber-50" };
  return <article className={`min-w-0 rounded-2xl border p-4 shadow-sm ${toneClasses[tone]}`} data-finance-kpi-card="true"><p className="text-sm font-semibold text-slate-500">{label}</p><p className="mt-2 break-words text-2xl font-black text-slate-950">{value}</p>{helper ? <p className="mt-2 text-xs leading-5 text-slate-600">{helper}</p> : null}</article>;
}

function LoadingState({ title }: { title: string }) {
  return <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label={title} data-finance-loading-state="true">{Array.from({ length: 8 }, (_, index) => <div key={index} className="h-32 animate-pulse rounded-2xl bg-white shadow-sm" />)}</section>;
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-center shadow-sm" data-finance-empty-state="true"><h2 className="text-xl font-black text-slate-950">{title}</h2><p className="mx-auto mt-2 max-w-2xl text-sm text-slate-600">{description}</p></section>;
}

function FinanceCards({ summary, currencyCode }: { summary: FinanceSummary; currencyCode: string }) {
  const { t } = useI18n();
  return (
    <section className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label={t("finance.kpiSection")}>
      <KpiCard label={t("finance.revenue")} value={formatMoney(summary.revenue, currencyCode)} helper={t("finance.revenueHelper")} />
      <KpiCard label={t("finance.grossProfit")} value={formatMoney(summary.gross_profit, currencyCode)} helper={t("finance.grossProfitHelper")} tone="profit" />
      <KpiCard label={t("finance.netProfit")} value={formatMoney(summary.net_profit, currencyCode)} helper={t("finance.netProfitHelper")} tone="profit" />
      <KpiCard label={t("finance.adSpend")} value={formatMoney(summary.ad_spend, currencyCode)} helper={t("finance.adSpendHelper")} tone="warning" />
      <KpiCard label={t("finance.manualExpenses")} value={formatMoney(summary.manual_expenses, currencyCode)} helper={t("finance.manualAdjustmentsHelper")} />
      <KpiCard label={t("finance.manualRefunds")} value={formatMoney(summary.manual_refunds, currencyCode)} />
      <KpiCard label={t("finance.manualDiscounts")} value={formatMoney(summary.manual_discounts, currencyCode)} />
      <KpiCard label={t("finance.manualFees")} value={formatMoney(summary.manual_fees, currencyCode)} />
      <KpiCard label={t("finance.cogs")} value={formatMoney(summary.cogs, currencyCode)} />
      <KpiCard label={t("finance.shippingCost")} value={formatMoney(summary.shipping_cost, currencyCode)} />
      <KpiCard label={t("finance.profitMargin")} value={formatPercent(summary.profit_margin)} helper={t("finance.safeZeroDenominator")} />
      <KpiCard label={t("finance.averageOrderValue")} value={summary.average_order_value ? formatMoney(summary.average_order_value, currencyCode) : "—"} />
    </section>
  );
}

function AdjustmentForm({ onSubmit, isSaving, editing }: { onSubmit: (payload: FinanceAdjustmentPayload) => void; isSaving: boolean; editing: FinanceAdjustment | null }) {
  const { t } = useI18n();
  const [form, setForm] = useState(() => editing ? { type: editing.type, category: editing.category, amount: editing.amount, occurred_at: editing.occurred_at.slice(0, 10), title: editing.title, description: editing.description ?? "" } : initialForm);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({ ...form, currency: "UAH", occurred_at: `${form.occurred_at}T12:00:00.000Z`, description: form.description || null });
    if (!editing) setForm(initialForm);
  }
  return (
    <form className="grid gap-3 rounded-2xl border border-emerald-100 bg-emerald-50 p-4" onSubmit={submit} data-finance-adjustment-form="expense-refund-discount-fee">
      <div className="grid gap-3 md:grid-cols-4">
        <label className="grid gap-1 text-sm font-bold text-slate-700">{t("finance.adjustmentType")}<select className="rounded-xl border border-slate-200 px-3 py-2" value={form.type} onChange={(event) => setForm((current) => ({ ...current, type: event.target.value as FinanceAdjustmentType }))}>{adjustmentTypes.map((type) => <option key={type} value={type}>{t(`finance.adjustmentTypes.${type}`)}</option>)}</select></label>
        <label className="grid gap-1 text-sm font-bold text-slate-700">{t("finance.adjustmentCategory")}<select className="rounded-xl border border-slate-200 px-3 py-2" value={form.category} onChange={(event) => setForm((current) => ({ ...current, category: event.target.value as FinanceAdjustmentCategory }))}>{adjustmentCategories.map((category) => <option key={category} value={category}>{t(`finance.adjustmentCategories.${category}`)}</option>)}</select></label>
        <label className="grid gap-1 text-sm font-bold text-slate-700">{t("finance.amount")}<input className="rounded-xl border border-slate-200 px-3 py-2" min="0.01" step="0.01" type="number" value={form.amount} onChange={(event) => setForm((current) => ({ ...current, amount: event.target.value }))} required /></label>
        <label className="grid gap-1 text-sm font-bold text-slate-700">{t("finance.occurredAt")}<input className="rounded-xl border border-slate-200 px-3 py-2" type="date" value={form.occurred_at} onChange={(event) => setForm((current) => ({ ...current, occurred_at: event.target.value }))} required /></label>
      </div>
      <label className="grid gap-1 text-sm font-bold text-slate-700">{t("finance.adjustmentTitle")}<input className="rounded-xl border border-slate-200 px-3 py-2" value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} required /></label>
      <label className="grid gap-1 text-sm font-bold text-slate-700">{t("finance.adjustmentDescription")}<textarea className="min-h-20 rounded-xl border border-slate-200 px-3 py-2" value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} /></label>
      <button className="min-h-11 rounded-xl bg-emerald-700 px-4 py-2 font-black text-white disabled:opacity-60" disabled={isSaving} type="submit">{isSaving ? t("common.saving") : editing ? t("finance.updateAdjustment") : t("finance.createAdjustment")}</button>
    </form>
  );
}

export default function FinancePage() {
  const { t, locale } = useI18n();
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspace, currentWorkspaceId, status: authStatus } = useAuth();
  const [preset, setPreset] = useState<DateRangePreset>("last30");
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");
  const [editing, setEditing] = useState<FinanceAdjustment | null>(null);
  const presetRange = useMemo(() => dateRangeForPreset(preset), [preset]);
  const dateFrom = preset === "custom" ? customFrom : presetRange.date_from;
  const dateTo = preset === "custom" ? customTo : presetRange.date_to;
  const enabled = authStatus === "authenticated" && Boolean(currentUser) && Boolean(currentWorkspaceId) && Boolean(dateFrom) && Boolean(dateTo);
  const currencyCode = currentWorkspace?.currency_code ?? "UAH";
  const canManageFinance = currentWorkspace?.role === "OWNER" || currentWorkspace?.role === "MANAGER";
  const summary = useQuery({ queryKey: ["finance-summary", currentWorkspaceId, dateFrom, dateTo], queryFn: () => fetchFinanceSummary(dateFrom, dateTo), enabled });
  const trends = useQuery({ queryKey: ["finance-trends", currentWorkspaceId, dateFrom, dateTo], queryFn: () => fetchFinanceTrends(dateFrom, dateTo), enabled });
  const adjustments = useQuery({ queryKey: ["finance-adjustments", currentWorkspaceId, dateFrom, dateTo], queryFn: () => fetchFinanceAdjustments(dateFrom, dateTo), enabled });
  const invalidateFinance = () => { queryClient.invalidateQueries({ queryKey: ["finance-summary", currentWorkspaceId] }); queryClient.invalidateQueries({ queryKey: ["finance-trends", currentWorkspaceId] }); queryClient.invalidateQueries({ queryKey: ["finance-adjustments", currentWorkspaceId] }); };
  const createMutation = useMutation({ mutationFn: createFinanceAdjustment, onSuccess: () => { invalidateFinance(); } });
  const updateMutation = useMutation({ mutationFn: (payload: FinanceAdjustmentPayload) => updateFinanceAdjustment(editing?.id ?? "", payload), onSuccess: () => { setEditing(null); invalidateFinance(); } });
  const deleteMutation = useMutation({ mutationFn: deleteFinanceAdjustment, onSuccess: invalidateFinance });
  const hasNoOrders = summary.data?.orders_count === 0;
  const warningText = (warning: { message: string; message_uk: string }) => (locale === "uk" ? warning.message_uk : warning.message);

  return (
    <main className="sellora-mobile-page min-h-screen w-full max-w-full min-w-0 overflow-x-hidden bg-[#F8F7FC] p-4 text-slate-950 sm:p-6">
      <div className="mx-auto grid w-full min-w-0 max-w-7xl gap-6 overflow-hidden">
        <header className="rounded-2xl bg-white p-5 shadow-sm sm:p-6"><p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-600">{t("finance.eyebrow")}</p><h1 className="mt-2 text-2xl font-black leading-tight sm:text-3xl">{t("finance.title")}</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{t("finance.subtitle")}</p><div className="mt-4 grid gap-3 rounded-2xl border border-emerald-100 bg-emerald-50 p-4 text-sm leading-6 text-emerald-950" data-finance-manual-csv-warning="meta-ads-api-not-active"><p className="font-bold">{t("finance.netProfitExplanation")}</p><p>{t("finance.adSpendManualCsvWarning")}</p><p>{t("finance.operationalNotAccounting")}</p><p>{t("finance.manualAdjustmentsExplanation")}</p></div></header>
        <section className="grid gap-3 rounded-2xl bg-white p-4 shadow-sm" data-finance-period-filter="true"><div className="flex flex-wrap gap-2">{dateRangePresetKeys().map((key) => <button key={key} className={`rounded-xl px-3 py-2 text-sm font-bold transition ${preset === key ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`} onClick={() => setPreset(key)} type="button">{t(`dateRange.${key}`)}</button>)}</div>{preset === "custom" ? <div className="grid gap-3 sm:grid-cols-2"><label className="grid gap-1 text-sm font-semibold text-slate-700">{t("finance.dateFrom")}<input className="rounded-xl border border-slate-200 px-3 py-2" type="date" value={customFrom} onChange={(event) => setCustomFrom(event.target.value)} /></label><label className="grid gap-1 text-sm font-semibold text-slate-700">{t("finance.dateTo")}<input className="rounded-xl border border-slate-200 px-3 py-2" type="date" value={customTo} onChange={(event) => setCustomTo(event.target.value)} /></label></div> : null}<p className="text-sm text-slate-500">{t("finance.selectedPeriod")}: {dateFrom || "—"} — {dateTo || "—"}</p></section>
        {summary.isLoading ? <LoadingState title={t("finance.kpiSection")} /> : null}
        {summary.isError ? <section className="rounded-2xl border border-rose-100 bg-rose-50 p-5 text-rose-950" data-finance-error-state="true"><h2 className="text-lg font-black">{t("finance.errorTitle")}</h2><p className="mt-2 text-sm">{safeApiErrorMessage(summary.error, t("finance.errorDescription"))}</p><button className="mt-4 rounded-xl bg-rose-700 px-4 py-2 text-sm font-bold text-white" onClick={() => summary.refetch()} type="button">{t("actions.retry")}</button></section> : null}
        {summary.data ? <FinanceCards summary={summary.data} currencyCode={currencyCode} /> : null}
        {summary.data ? <section className="grid gap-3 rounded-2xl bg-white p-5 shadow-sm" data-finance-breakdown="net-profit-breakdown-period-comparison"><div><p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-600">{t("finance.breakdownEyebrow")}</p><h2 className="mt-1 text-xl font-black">{t("finance.breakdownTitle")}</h2><p className="mt-1 text-sm text-slate-600">{t("finance.breakdownDescription")}</p></div><div className="grid gap-2 md:grid-cols-3">{summary.data.breakdown.map((item) => <div key={item.key} className="rounded-xl border border-slate-100 bg-slate-50 p-3"><p className="text-sm font-bold text-slate-500">{t(`finance.breakdown.${item.key}`)}</p><p className="mt-1 text-lg font-black">{formatMoney(item.amount, currencyCode)}</p><p className="text-xs text-slate-500">{item.share_of_revenue ? `${formatPercent(item.share_of_revenue)} ${t("finance.ofRevenue")}` : "—"}</p></div>)}</div><div className="rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-950"><p className="font-black">{t("finance.periodComparison")}</p><p className="mt-1">{t("finance.netProfitChange")}: {formatMoney(trends.data?.net_profit_change.change ?? null, currencyCode)} ({formatPercent(trends.data?.net_profit_change.change_percent ?? null)})</p><p>{t("finance.revenueChange")}: {formatMoney(trends.data?.revenue_change.change ?? null, currencyCode)} ({formatPercent(trends.data?.revenue_change.change_percent ?? null)})</p></div></section> : null}
        <section className="grid gap-4 rounded-2xl bg-white p-5 shadow-sm" data-finance-adjustments-ui="manual-expenses-refunds-discounts-fees"><div><p className="text-sm font-semibold uppercase tracking-[0.2em] text-purple-600">{t("finance.adjustmentsEyebrow")}</p><h2 className="mt-1 text-xl font-black">{t("finance.adjustmentsTitle")}</h2><p className="mt-1 text-sm text-slate-600">{t("finance.adjustmentsDescription")}</p></div>{canManageFinance ? <AdjustmentForm key={editing?.id ?? "new"} editing={editing} isSaving={createMutation.isPending || updateMutation.isPending} onSubmit={(payload) => editing ? updateMutation.mutate(payload) : createMutation.mutate(payload)} /> : <p className="rounded-xl bg-slate-50 p-3 text-sm text-slate-600">{t("finance.adjustmentsReadOnly")}</p>}{createMutation.isError || updateMutation.isError || deleteMutation.isError ? <p className="rounded-xl bg-rose-50 p-3 text-sm font-semibold text-rose-700">{t("finance.adjustmentSaveError")}</p> : null}{adjustments.isLoading ? <div className="h-24 animate-pulse rounded-xl bg-slate-100" data-finance-adjustments-loading="true" /> : null}{adjustments.data?.items.length === 0 ? <div className="rounded-xl border border-dashed border-slate-300 p-4 text-sm text-slate-600" data-finance-adjustments-empty="true">{t("finance.adjustmentsEmpty")}</div> : null}<div className="grid gap-2">{adjustments.data?.items.map((item) => <article key={item.id} className="grid gap-2 rounded-xl border border-slate-100 p-3 md:grid-cols-[1fr_auto]"><div><p className="font-black">{item.title}</p><p className="text-sm text-slate-600">{t(`finance.adjustmentTypes.${item.type}`)} · {t(`finance.adjustmentCategories.${item.category}`)} · {item.occurred_at.slice(0, 10)}</p>{item.description ? <p className="mt-1 text-sm text-slate-500">{item.description}</p> : null}</div><div className="flex flex-wrap items-center gap-2 md:justify-end"><span className="font-black">{formatMoney(item.amount, item.currency)}</span>{canManageFinance ? <><button className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold" onClick={() => setEditing(item)} type="button">{t("actions.edit")}</button><button className="rounded-lg bg-rose-50 px-3 py-2 text-sm font-bold text-rose-700" onClick={() => deleteMutation.mutate(item.id)} type="button">{t("actions.delete")}</button></> : null}</div></article>)}</div></section>
        {summary.data ? <section className="grid gap-3 rounded-2xl bg-white p-5 shadow-sm" data-finance-data-quality-warnings="true"><div><p className="text-sm font-semibold uppercase tracking-[0.2em] text-amber-600">{t("finance.dataQualityEyebrow")}</p><h2 className="mt-1 text-xl font-black text-slate-950">{t("finance.dataQualityTitle")}</h2><p className="mt-1 text-sm text-slate-600">{t("finance.dataQualityDescription")}</p></div><ul className="grid gap-2">{summary.data.data_quality_warnings.map((warning) => <li key={warning.code} className="rounded-xl border border-amber-100 bg-amber-50 p-3 text-sm text-amber-950">{warningText(warning)}</li>)}</ul></section> : null}
        {hasNoOrders ? <EmptyState title={t("finance.emptyTitle")} description={t("finance.emptyDescription")} /> : null}
      </div>
    </main>
  );
}
