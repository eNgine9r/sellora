"use client";

import { useMemo } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import type { AdvertisingTrendPoint } from "@/types/advertising";

export function AdvertisingTrendChart({
  data, currencyCode = "UAH",
}: {
  data: AdvertisingTrendPoint[]; currencyCode?: string;
}) {
  const { t } = useI18n();
  const rows = useMemo(() => data.map(item => ({
    date: item.date,
    spend: Number(item.spend) || 0,
    revenue: Number(item.revenue) || 0,
  })), [data]);
  const shortDate = (date: string) => {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date);
    return match ? match[3] + "." + match[2] : date;
  };

  return (
    <section className="min-w-0 overflow-hidden rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm sm:p-5" data-advertising-visual-trend>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-text-primary">{t("adsDashboard.trendTitle")}</h2>
          <p className="mt-1 text-xs text-text-secondary">{t("adsDashboard.trendCaption")}</p>
        </div>
        <div className="flex items-center gap-4 text-xs font-medium text-text-secondary">
          <span className="flex items-center gap-2"><span className="size-2.5 rounded-full bg-violet-500" />{t("adsDashboard.spend")}</span>
          <span className="flex items-center gap-2"><span className="size-2.5 rounded-full bg-emerald-500" />{t("adsDashboard.revenue")}</span>
        </div>
      </div>
      {rows.length ? (
        <div className="mt-5 h-[250px] w-full min-w-0 sm:h-[295px]" role="img" aria-label={t("adsDashboard.trendTitle")}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={rows} margin={{ top: 8, right: 10, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="sellora-spend-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.25} /><stop offset="100%" stopColor="#8b5cf6" stopOpacity={0} /></linearGradient>
                <linearGradient id="sellora-revenue-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#10b981" stopOpacity={0.2} /><stop offset="100%" stopColor="#10b981" stopOpacity={0} /></linearGradient>
              </defs>
              <CartesianGrid vertical={false} strokeDasharray="3 5" stroke="#94a3b8" strokeOpacity={0.16} />
              <XAxis dataKey="date" tickFormatter={shortDate} tickLine={false} axisLine={false} minTickGap={26} tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <YAxis tickLine={false} axisLine={false} width={52} tick={{ fill: "#94a3b8", fontSize: 11 }} tickFormatter={value => Number(value).toLocaleString("uk-UA", { notation: "compact", maximumFractionDigits: 1 })} />
              <Tooltip
                labelFormatter={value => shortDate(String(value))}
                formatter={(value, name) => [formatMoney(Number(value), currencyCode), name === "spend" ? t("adsDashboard.spend") : t("adsDashboard.revenue")]}
                contentStyle={{ backgroundColor: "#17182b", border: "1px solid #383a56", borderRadius: 14, color: "#f8fafc", fontSize: 12 }}
                labelStyle={{ color: "#cbd5e1" }}
              />
              <Area type="monotone" dataKey="spend" stroke="#8b5cf6" strokeWidth={2.5} fill="url(#sellora-spend-fill)" dot={false} activeDot={{ r: 4 }} />
              <Area type="monotone" dataKey="revenue" stroke="#10b981" strokeWidth={2.5} fill="url(#sellora-revenue-fill)" dot={false} activeDot={{ r: 4 }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="mt-5 flex h-[230px] items-center justify-center rounded-xl border border-dashed border-border-subtle p-4 text-center text-sm text-text-secondary">{t("adsDashboard.noTrendData")}</div>
      )}
    </section>
  );
}
