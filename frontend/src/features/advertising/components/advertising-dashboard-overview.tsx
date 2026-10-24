"use client";

import { ArrowUpRight, CircleHelp, MessageCircle, MousePointerClick, ReceiptText, ShieldCheck, TrendingUp, Wallet } from "lucide-react";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import type { AdvertisingSummary, CampaignPerformance } from "@/types/advertising";

const number = (value: string | number | null | undefined) => {
  const parsed = Number(value);
  return value == null || !Number.isFinite(parsed) ? 0 : parsed;
};

function MetricTile({
  title, value, caption, icon: Icon, accent,
}: {
  title: string; value: string; caption: string; icon: typeof Wallet; accent?: boolean;
}) {
  return (
    <div className={"relative flex min-w-0 flex-col justify-between overflow-hidden rounded-2xl border p-4 sm:p-5 " +
      (accent ? "border-indigo-400/40 bg-gradient-to-br from-indigo-600 via-violet-600 to-fuchsia-700 text-white shadow-lg shadow-indigo-600/15"
        : "border-border-subtle bg-surface-1 text-text-primary shadow-sm")}>
      {accent ? <div aria-hidden="true" className="pointer-events-none absolute -right-10 -top-14 size-40 rounded-full border border-white/20 bg-white/10 blur-xl" /> : null}
      <div className="flex items-center justify-between gap-2">
        <span className={"text-xs font-semibold tracking-wide " + (accent ? "text-white/75" : "text-text-secondary")}>{title}</span>
        <span className={"flex size-9 items-center justify-center rounded-xl " + (accent ? "bg-white/15" : "bg-surface-2 text-indigo-500")}>
          <Icon className="size-[18px]" aria-hidden="true" />
        </span>
      </div>
      <div className="mt-5 min-w-0">
        <p className="truncate text-2xl font-bold tracking-tight sm:text-[28px]" title={value}>{value}</p>
        <p className={"mt-1.5 min-h-8 text-xs leading-4 " + (accent ? "text-white/75" : "text-text-secondary")}>{caption}</p>
      </div>
    </div>
  );
}

export function AdvertisingDashboardOverview({
  summary, campaigns, currencyCode, sourceLabel, loading,
}: {
  summary?: AdvertisingSummary;
  campaigns: CampaignPerformance[];
  currencyCode: string;
  sourceLabel: string;
  loading: boolean;
}) {
  const { t } = useI18n();
  const spend = number(summary?.total_spend);
  const messages = summary?.total_messages ?? 0;
  const orderCount = summary?.total_orders ?? 0;
  const revenue = number(summary?.total_revenue);
  const hasAttributedRevenue = orderCount > 0 || revenue > 0;
  const costPerMessage = messages > 0 ? spend / messages : null;
  const roas = spend > 0 && hasAttributedRevenue ? revenue / spend : null;
  const top = [...campaigns]
    .filter((item) => number(item.spend) > 0)
    .sort((a, b) => number(b.spend) - number(a.spend))
    .slice(0, 5);
  const highestSpend = top.length ? number(top[0].spend) : 0;
  return (
    <div className="grid min-w-0 gap-4" data-advertising-dashboard-overview>
      <div className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <MetricTile title={t("adsDashboard.spend")} value={loading ? "—" : formatMoney(summary?.total_spend, currencyCode)}
          caption={t("adsDashboard.spendCaption")} icon={Wallet} accent />
        <MetricTile title={t("adsDashboard.messages")} value={loading ? "—" : messages.toLocaleString()}
          caption={t("adsDashboard.messagesCaption")} icon={MessageCircle} />
        <MetricTile title={t("adsDashboard.costPerMessage")} value={loading || costPerMessage == null ? "—" : formatMoney(costPerMessage, currencyCode)}
          caption={t("adsDashboard.costPerMessageCaption")} icon={MousePointerClick} />
        <MetricTile title={t("adsDashboard.orders")} value={loading ? "—" : orderCount.toLocaleString()}
          caption={t("adsDashboard.ordersCaption")} icon={ReceiptText} />
        <MetricTile title={t("adsDashboard.revenue")} value={loading ? "—" : formatMoney(summary?.total_revenue, currencyCode)}
          caption={t("adsDashboard.revenueCaption")} icon={TrendingUp} />
        <MetricTile title="ROAS" value={loading || roas == null ? "—" : roas.toFixed(2) + "×"}
          caption={t("adsDashboard.roasCaption")} icon={ArrowUpRight} />
      </div>

      <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(300px,0.52fr)]">
        <section className="min-w-0 rounded-2xl border border-border-subtle bg-surface-1 p-5 shadow-sm" aria-label={t("adsDashboard.topCampaigns")}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-base font-bold text-text-primary">{t("adsDashboard.topCampaigns")}</h2>
            <span className="rounded-full bg-surface-2 px-2.5 py-1 text-xs font-medium text-text-secondary">{t("adsDashboard.spendRanking")}</span>
          </div>
          {top.length ? (
            <div className="mt-5 grid gap-5">
              {top.map((item, index) => (
                <div key={item.campaign_id} className="grid min-w-0 gap-2">
                  <div className="flex min-w-0 items-center justify-between gap-3 text-sm">
                    <p className="min-w-0 truncate font-medium text-text-primary" title={item.campaign_name}>
                      <span className="mr-2 text-xs text-text-muted">{String(index + 1).padStart(2, "0")}</span>{item.campaign_name}
                    </p>
                    <span className="shrink-0 font-semibold tabular-nums text-text-primary">{formatMoney(item.spend, currencyCode)}</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-surface-2" aria-hidden="true">
                    <div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-400" style={{ width: Math.max(3, 100 * number(item.spend) / highestSpend) + "%" }} />
                  </div>
                  <p className="text-xs text-text-muted">{t("adsDashboard.messages")}: {item.messages} · {t("adsDashboard.orders")}: {item.orders}</p>
                </div>
              ))}
            </div>
          ) : <p className="mt-5 rounded-xl border border-dashed border-border-subtle px-4 py-8 text-center text-sm text-text-secondary">{t("adsDashboard.noCampaignData")}</p>}
        </section>
        <section className="flex min-w-0 flex-col gap-4 rounded-2xl border border-border-subtle bg-surface-1 p-5 shadow-sm" aria-label={t("adsDashboard.dataQualityTitle")}>
          <div className="flex items-center gap-2">
            <ShieldCheck className="size-5 text-indigo-500" aria-hidden="true" />
            <h2 className="text-base font-bold text-text-primary">{t("adsDashboard.dataQualityTitle")}</h2>
          </div>
          <div className="rounded-xl bg-surface-2 p-4">
            <p className="text-xs font-medium text-text-secondary">{t("adsDashboard.source")}</p>
            <p className="mt-1 text-sm font-semibold text-text-primary">{sourceLabel}</p>
          </div>
          <div className="flex gap-2 text-sm leading-6 text-text-secondary">
            <CircleHelp className="mt-1 size-4 shrink-0 text-indigo-500" aria-hidden="true" />
            <p>{t("adsDashboard.attributionNotice")}</p>
          </div>
          {spend > 0 && !hasAttributedRevenue ? (
            <p className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-sm leading-5 text-text-primary" role="status">{t("adsDashboard.noAttributionNotice")}</p>
          ) : null}
        </section>
      </div>
    </div>
  );
}
