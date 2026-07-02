"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { dateRangeForPreset, dateRangePresetKeys, type DateRangePreset } from "@/lib/date-range-presets";
import { formatMoney } from "@/lib/currency";
import { safeApiErrorMessage } from "@/services/api";
import { fetchFinanceSummary } from "@/services/finance";
import { useI18n } from "@/i18n/provider";
import type { FinanceSummary } from "@/types/finance";

function formatPercent(value?: string | null) {
  if (value == null) return "—";
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "—";
  return `${amount.toLocaleString("uk-UA", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

function KpiCard({ label, value, helper, tone = "default" }: { label: string; value: string; helper?: string; tone?: "default" | "profit" | "warning" }) {
  const toneClasses = {
    default: "border-slate-100 bg-white",
    profit: "border-emerald-100 bg-emerald-50",
    warning: "border-amber-100 bg-amber-50",
  };
  return (
    <article className={`min-w-0 rounded-2xl border p-4 shadow-sm ${toneClasses[tone]}`} data-finance-kpi-card="true">
      <p className="text-sm font-semibold text-slate-500">{label}</p>
      <p className="mt-2 break-words text-2xl font-black text-slate-950">{value}</p>
      {helper ? <p className="mt-2 text-xs leading-5 text-slate-600">{helper}</p> : null}
    </article>
  );
}

function LoadingState({ title }: { title: string }) {
  return (
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label={title} data-finance-loading-state="true">
      {Array.from({ length: 8 }, (_, index) => (
        <div key={index} className="h-32 animate-pulse rounded-2xl bg-white shadow-sm" />
      ))}
    </section>
  );
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-center shadow-sm" data-finance-empty-state="true">
      <h2 className="text-xl font-black text-slate-950">{title}</h2>
      <p className="mx-auto mt-2 max-w-2xl text-sm text-slate-600">{description}</p>
    </section>
  );
}

function FinanceCards({ summary, currencyCode }: { summary: FinanceSummary; currencyCode: string }) {
  const { t } = useI18n();
  return (
    <section className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label={t("finance.kpiSection")}>
      <KpiCard label={t("finance.revenue")} value={formatMoney(summary.revenue, currencyCode)} helper={t("finance.revenueHelper")} />
      <KpiCard label={t("finance.grossProfit")} value={formatMoney(summary.gross_profit, currencyCode)} helper={t("finance.grossProfitHelper")} tone="profit" />
      <KpiCard label={t("finance.netProfit")} value={formatMoney(summary.net_profit, currencyCode)} helper={t("finance.netProfitHelper")} tone="profit" />
      <KpiCard label={t("finance.adSpend")} value={formatMoney(summary.ad_spend, currencyCode)} helper={t("finance.adSpendHelper")} tone="warning" />
      <KpiCard label={t("finance.cogs")} value={formatMoney(summary.cogs, currencyCode)} />
      <KpiCard label={t("finance.shippingCost")} value={formatMoney(summary.shipping_cost, currencyCode)} />
      <KpiCard label={t("finance.profitMargin")} value={formatPercent(summary.profit_margin)} helper={t("finance.safeZeroDenominator")} />
      <KpiCard label={t("finance.averageOrderValue")} value={summary.average_order_value ? formatMoney(summary.average_order_value, currencyCode) : "—"} />
      <KpiCard label={t("finance.ordersCount")} value={String(summary.orders_count)} />
      <KpiCard label={t("finance.paidOrdersCount")} value={String(summary.paid_orders_count)} />
      <KpiCard label={t("finance.refunds")} value={formatMoney(summary.refunds, currencyCode)} />
      <KpiCard label={t("finance.otherExpenses")} value={formatMoney(summary.other_expenses, currencyCode)} />
    </section>
  );
}

export default function FinancePage() {
  const { t, locale } = useI18n();
  const { currentUser, currentWorkspace, currentWorkspaceId, status: authStatus } = useAuth();
  const [preset, setPreset] = useState<DateRangePreset>("last30");
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");
  const presetRange = useMemo(() => dateRangeForPreset(preset), [preset]);
  const dateFrom = preset === "custom" ? customFrom : presetRange.date_from;
  const dateTo = preset === "custom" ? customTo : presetRange.date_to;
  const enabled = authStatus === "authenticated" && Boolean(currentUser) && Boolean(currentWorkspaceId) && Boolean(dateFrom) && Boolean(dateTo);
  const currencyCode = currentWorkspace?.currency_code ?? "UAH";
  const summary = useQuery({ queryKey: ["finance-summary", currentWorkspaceId, dateFrom, dateTo], queryFn: () => fetchFinanceSummary(dateFrom, dateTo), enabled });
  const hasNoOrders = summary.data?.orders_count === 0;
  const warningText = (warning: { message: string; message_uk: string }) => (locale === "uk" ? warning.message_uk : warning.message);

  return (
    <main className="sellora-mobile-page min-h-screen w-full max-w-full min-w-0 overflow-x-hidden bg-[#F8F7FC] p-4 text-slate-950 sm:p-6">
      <div className="mx-auto grid w-full min-w-0 max-w-7xl gap-6 overflow-hidden">
        <header className="rounded-2xl bg-white p-5 shadow-sm sm:p-6">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-600">{t("finance.eyebrow")}</p>
          <h1 className="mt-2 text-2xl font-black leading-tight sm:text-3xl">{t("finance.title")}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{t("finance.subtitle")}</p>
          <div className="mt-4 grid gap-3 rounded-2xl border border-emerald-100 bg-emerald-50 p-4 text-sm leading-6 text-emerald-950" data-finance-manual-csv-warning="meta-ads-api-not-active">
            <p className="font-bold">{t("finance.netProfitExplanation")}</p>
            <p>{t("finance.adSpendManualCsvWarning")}</p>
            <p>{t("finance.operationalNotAccounting")}</p>
          </div>
        </header>

        <section className="grid gap-3 rounded-2xl bg-white p-4 shadow-sm" data-finance-period-filter="true">
          <div className="flex flex-wrap gap-2">
            {dateRangePresetKeys().map((key) => (
              <button
                key={key}
                className={`rounded-xl px-3 py-2 text-sm font-bold transition ${preset === key ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}
                onClick={() => setPreset(key)}
                type="button"
              >
                {t(`dateRange.${key}`)}
              </button>
            ))}
          </div>
          {preset === "custom" ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="grid gap-1 text-sm font-semibold text-slate-700">
                {t("finance.dateFrom")}
                <input className="rounded-xl border border-slate-200 px-3 py-2" type="date" value={customFrom} onChange={(event) => setCustomFrom(event.target.value)} />
              </label>
              <label className="grid gap-1 text-sm font-semibold text-slate-700">
                {t("finance.dateTo")}
                <input className="rounded-xl border border-slate-200 px-3 py-2" type="date" value={customTo} onChange={(event) => setCustomTo(event.target.value)} />
              </label>
            </div>
          ) : null}
          <p className="text-sm text-slate-500">{t("finance.selectedPeriod")}: {dateFrom || "—"} — {dateTo || "—"}</p>
        </section>

        {summary.isLoading ? <LoadingState title={t("finance.kpiSection")} /> : null}

        {summary.isError ? (
          <section className="rounded-2xl border border-rose-100 bg-rose-50 p-5 text-rose-950" data-finance-error-state="true">
            <h2 className="text-lg font-black">{t("finance.errorTitle")}</h2>
            <p className="mt-2 text-sm">{safeApiErrorMessage(summary.error, t("finance.errorDescription"))}</p>
            <button className="mt-4 rounded-xl bg-rose-700 px-4 py-2 text-sm font-bold text-white" onClick={() => summary.refetch()} type="button">{t("actions.retry")}</button>
          </section>
        ) : null}

        {summary.data ? <FinanceCards summary={summary.data} currencyCode={currencyCode} /> : null}

        {summary.data ? (
          <section className="grid gap-3 rounded-2xl bg-white p-5 shadow-sm" data-finance-data-quality-warnings="true">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-amber-600">{t("finance.dataQualityEyebrow")}</p>
              <h2 className="mt-1 text-xl font-black text-slate-950">{t("finance.dataQualityTitle")}</h2>
              <p className="mt-1 text-sm text-slate-600">{t("finance.dataQualityDescription")}</p>
            </div>
            <ul className="grid gap-2">
              {summary.data.data_quality_warnings.map((warning) => (
                <li key={warning.code} className="rounded-xl border border-amber-100 bg-amber-50 p-3 text-sm text-amber-950">{warningText(warning)}</li>
              ))}
            </ul>
          </section>
        ) : null}

        {hasNoOrders ? <EmptyState title={t("finance.emptyTitle")} description={t("finance.emptyDescription")} /> : null}
      </div>
    </main>
  );
}
