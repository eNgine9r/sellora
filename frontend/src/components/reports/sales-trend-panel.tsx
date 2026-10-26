"use client";

import { useMemo } from "react";
import { Activity, CalendarDays, TrendingUp } from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import { toFiniteNumber } from "@/lib/analytics-formulas";
import type { SalesReportDailyRow } from "@/types/analytics";

type Props = {
  rows: SalesReportDailyRow[];
  currencyCode: string;
  loading: boolean;
};

export function SalesTrendPanel({ rows, currencyCode, loading }: Props) {
  const { t, locale } = useI18n();
  const values = useMemo(() => rows
    .map((row) => ({ date: row.date, revenue: Math.max(0, toFiniteNumber(row.revenue)), orders: row.orders }))
    .sort((a, b) => a.date.localeCompare(b.date)), [rows]);
  const top = useMemo(() => values.reduce<(typeof values)[number] | undefined>(
    (best, item) => !best || item.revenue > best.revenue ? item : best, undefined,
  ), [values]);
  const currencyFormatter = (value: number) => formatMoney(value, currencyCode);
  const dayFormatter = (day: string) => {
    const [year, month, date] = day.split("-").map(Number);
    if (!year || !month || !date) return day;
    return new Intl.DateTimeFormat(locale === "uk" ? "uk-UA" : "en-US", { day: "numeric", month: "short" })
      .format(new Date(Date.UTC(year, month - 1, date, 12)));
  };

  return <section className="min-w-0 overflow-hidden rounded-[24px] border border-border-subtle bg-surface-1 p-4 shadow-[var(--shadow-card)] sm:p-5 lg:p-6" aria-labelledby="reports-trend-heading" data-reports-sales-trend>
    <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-primary">
          <Activity className="h-4 w-4" aria-hidden="true" />{t("analytics.modern.trendEyebrow")}
        </span>
        <h2 id="reports-trend-heading" className="mt-2 text-lg font-bold text-text-primary lg:text-xl">{t("analytics.modern.trendTitle")}</h2>
        <p className="mt-1 text-xs leading-5 text-text-muted">{t("analytics.modern.trendDescription")}</p>
      </div>
      <div className="flex items-center gap-2 rounded-xl border border-border-subtle bg-surface-2 px-3 py-2 text-xs font-semibold text-text-secondary">
        <span className="h-2 w-2 rounded-full bg-primary" aria-hidden="true" />{t("analytics.metrics.revenue")}
      </div>
    </div>
    {loading ? <div className="h-[235px] animate-pulse rounded-2xl bg-surface-2" aria-label={t("analytics.reports.loading")} /> :
      values.length === 0 ? <div className="flex min-h-[235px] flex-col items-center justify-center rounded-2xl border border-dashed border-border-subtle bg-surface-2/40 px-6 text-center">
        <TrendingUp className="mb-3 h-8 w-8 text-primary/60" aria-hidden="true" />
        <h3 className="text-sm font-semibold text-text-primary">{t("analytics.modern.trendEmpty")}</h3>
        <p className="mt-1 max-w-sm text-xs leading-5 text-text-muted">{t("analytics.modern.trendEmptyHelp")}</p>
      </div> : <div className="h-[235px] min-w-0 sm:h-[260px]" role="img" aria-label={t("analytics.modern.trendChartAria", { count: values.length })}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={values} margin={{ top: 10, right: 8, left: -8, bottom: 0 }}>
            <defs>
              <linearGradient id="reportsRevenueFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--primary-solid)" stopOpacity={0.32} />
                <stop offset="95%" stopColor="var(--primary-solid)" stopOpacity={0.01} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} stroke="var(--border-subtle)" strokeDasharray="3 6" />
            <XAxis dataKey="date" tickFormatter={dayFormatter} tick={{ fill: "var(--text-muted)", fontSize: 11 }} minTickGap={28} tickLine={false} axisLine={false} dy={8} />
            <YAxis tickFormatter={(value: number) => new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(value)}
              tick={{ fill: "var(--text-muted)", fontSize: 11 }} width={52} tickLine={false} axisLine={false} />
            <Tooltip
              labelFormatter={(label) => dayFormatter(String(label))}
              formatter={(value) => [currencyFormatter(Number(value ?? 0)), t("analytics.metrics.revenue")]}
              contentStyle={{ background: "var(--surface-elevated)", borderColor: "var(--border-default)", borderRadius: 14, color: "var(--text-primary)", boxShadow: "var(--shadow-card)" }}
              labelStyle={{ color: "var(--text-secondary)" }}
              itemStyle={{ color: "var(--text-primary)" }}
            />
            <Area type="monotone" dataKey="revenue" name={t("analytics.metrics.revenue")} stroke="var(--primary-solid)" strokeWidth={2.7} fill="url(#reportsRevenueFill)" dot={false} activeDot={{ r: 5 }} isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>}
    <div className="mt-4 grid grid-cols-2 divide-x divide-border-subtle rounded-xl border border-border-subtle bg-surface-2/50 py-3">
      <div className="min-w-0 px-4">
        <div className="flex items-center gap-1.5 text-xs text-text-muted"><CalendarDays className="h-3.5 w-3.5" />{t("analytics.modern.activeDays")}</div>
        <p className="mt-1 text-lg font-bold tabular-nums text-text-primary">{loading ? "—" : values.length}</p>
      </div>
      <div className="min-w-0 px-4">
        <div className="flex items-center gap-1.5 text-xs text-text-muted"><TrendingUp className="h-3.5 w-3.5" />{t("analytics.modern.peakDay")}</div>
        <p className="mt-1 truncate text-lg font-bold tabular-nums text-text-primary" title={top ? currencyFormatter(top.revenue) : undefined}>{loading ? "—" : top ? currencyFormatter(top.revenue) : "—"}</p>
        {top && !loading ? <p className="text-[11px] text-text-muted">{dayFormatter(top.date)}</p> : null}
      </div>
    </div>
  </section>;
}
