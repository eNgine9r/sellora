"use client";

import { useMemo } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, BarChart3, CheckCircle2, CircleHelp, Lightbulb, PackageSearch, ShieldCheck, TrendingUp } from "lucide-react";

import { WorkspaceHeader, WorkspacePage } from "@/components/crm-workspace";
import { DateRangeSelector } from "@/components/date-range-selector";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/states";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { useDateRange } from "@/providers/date-range-provider";
import { fetchAdvertisingReport, fetchBusinessInsights, fetchInventorySummary, fetchSalesReport } from "@/services/analytics";
import { BusinessInsight } from "@/types/analytics";

const priority: Record<string, number> = { critical: 0, warning: 1, info: 2, positive: 3 };
const allowedTargets = new Set(["/inventory", "/orders", "/leads", "/advertising", "/analytics", "/dashboard", "/finance", "/customers", "/products"]);
function money(value: string | number | null | undefined, locale: string, currency: string) {
  const amount = Number(value);
  return value == null || !Number.isFinite(amount) ? "—" : new Intl.NumberFormat(locale === "uk" ? "uk-UA" : "en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(amount);
}
function ratio(value: string | number | null | undefined) {
  const number = Number(value);
  return value == null || !Number.isFinite(number) ? "—" : `${number.toFixed(2)}×`;
}

export default function InsightsPage() {
  const { t, locale } = useI18n();
  const { range } = useDateRange();
  const { currentWorkspaceId, currentWorkspace, status } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const enabled = status === "authenticated" && !!workspaceId;
  const dates = [range.date_from || undefined, range.date_to || undefined] as const;
  const currency = currentWorkspace?.currency_code ?? "UAH";

  const insights = useQuery({ queryKey: ["insights-rules", workspaceId, ...dates], queryFn: () => fetchBusinessInsights(workspaceId, undefined, ...dates), enabled });
  const sales = useQuery({ queryKey: ["insights-sales", workspaceId, ...dates], queryFn: () => fetchSalesReport(workspaceId, undefined, ...dates), enabled });
  const advertising = useQuery({ queryKey: ["insights-advertising", workspaceId, ...dates], queryFn: () => fetchAdvertisingReport(workspaceId, undefined, ...dates), enabled });
  const inventory = useQuery({ queryKey: ["insights-inventory", workspaceId], queryFn: () => fetchInventorySummary(workspaceId), enabled });

  const sorted = useMemo(() => [...(insights.data?.insights ?? [])].sort((a, b) => (priority[a.type] ?? 2) - (priority[b.type] ?? 2)), [insights.data]);
  const warnings = sorted.filter((insight) => insight.type === "critical" || insight.type === "warning").length;
  const allReady = !insights.isLoading && !sales.isLoading && !advertising.isLoading && !inventory.isLoading;
  const hasError = insights.isError || sales.isError || advertising.isError || inventory.isError;
  const data = sales.data;
  const ads = advertising.data;
  const stock = inventory.data;
  const badges = [
    { label: t("insightHub.orders"), value: data?.orders_count ?? "—", detail: t("insightHub.orderContext"), icon: BarChart3 },
    { label: t("insightHub.revenue"), value: money(data?.revenue, locale, currency), detail: t("insightHub.revenueContext"), icon: TrendingUp },
    { label: t("insightHub.adSpend"), value: money(ads?.spend, locale, currency), detail: t("insightHub.adContext"), icon: BarChart3 },
    { label: t("insightHub.lowStock"), value: stock?.low_stock_count ?? "—", detail: t("insightHub.stockContext"), icon: PackageSearch },
  ];

  function description(item: BusinessInsight) {
    return t(item.description_key, {
      count: item.value ?? stock?.low_stock_count ?? 0,
      returns: data?.daily_rows.reduce((sum, row) => sum + row.returns, 0) ?? 0,
      cancelled: data?.cancelled_orders ?? 0,
    });
  }

  return <WorkspacePage>
    <WorkspaceHeader title={t("navigation.insights")} description={t("insightHub.subtitle")} actions={
      <Link href="/analytics" className="inline-flex min-h-11 w-fit items-center gap-2 rounded-xl border border-border-subtle bg-surface-1 px-4 text-sm font-semibold text-text-primary hover:bg-surface-hover">{t("insightHub.reports")}<ArrowRight className="h-4 w-4" /></Link>
    } />

    <section className="flex min-w-0 flex-col gap-2 rounded-2xl border border-border-subtle bg-surface-1 p-3 sm:flex-row sm:items-center sm:justify-between" aria-label={t("insightHub.period")}>
      <div className="flex items-center gap-2 text-sm font-medium text-text-secondary"><ShieldCheck className="h-4 w-4 text-primary" aria-hidden="true" />{t("insightHub.period")}<span className="text-xs text-text-muted">{range.date_from} — {range.date_to}</span></div>
      <DateRangeSelector compact />
    </section>

    {hasError ? <ErrorState description={t("insightHub.loadError")} onRetry={() => { void Promise.all([insights.refetch(), sales.refetch(), advertising.refetch(), inventory.refetch()]); }} /> : null}
    {!hasError && !allReady ? <LoadingSkeleton rows={4} title={t("insightHub.loading")} /> : null}
    {!hasError && allReady ? <>
      <div className="grid min-w-0 grid-cols-2 gap-2 sm:gap-3 xl:grid-cols-4" data-insight-metrics>
        {badges.map(({ label, value, detail, icon: Icon }) => <article key={label} className="min-w-0 rounded-2xl border border-border-subtle bg-surface-1 p-3 sm:p-4">
          <div className="flex items-center gap-2 text-xs font-medium text-text-muted"><Icon className="h-4 w-4 shrink-0" />{label}</div>
          <p className="mt-2 truncate text-xl font-semibold tabular-nums text-text-primary sm:text-2xl" title={String(value)}>{value}</p>
          <p className="mt-1 text-xs leading-5 text-text-muted">{detail}</p>
        </article>)}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h2 className="text-lg font-semibold text-text-primary">{t("insightHub.actionsTitle")}</h2>
          <p className="mt-1 text-sm text-text-muted">{warnings ? t("insightHub.issuesCount", { count: warnings }) : t("insightHub.noIssues")}</p>
        </div>
        {ads ? <div className="rounded-xl border border-border-subtle bg-surface-1 px-3 py-2 text-sm text-text-secondary"><span className="text-text-muted">ROAS · </span><strong className="tabular-nums text-text-primary">{ratio(ads.roas)}</strong></div> : null}
      </div>

      {sorted.length === 0 ? <EmptyState title={t("insightHub.emptyTitle")} description={t("insightHub.emptyDescription")} /> : null}
      {sorted.length > 0 ? <div className="grid min-w-0 gap-3 lg:grid-cols-2" data-insight-recommendations>
        {sorted.map((item) => {
          const critical = item.type === "critical";
          const warning = item.type === "warning";
          const good = item.type === "positive";
          const Icon = critical || warning ? AlertTriangle : good ? CheckCircle2 : Lightbulb;
          const href = allowedTargets.has(item.route ?? "") ? item.route! : "/analytics";
          const tone = critical ? "text-danger bg-[var(--danger-surface)]" : warning ? "text-warning bg-[var(--warning-surface)]" : good ? "text-success bg-[var(--success-surface)]" : "text-primary bg-primary/10";
          return <article key={item.key} className="flex min-w-0 flex-col gap-3 rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-[var(--shadow-card)] sm:p-5">
            <div className="flex min-w-0 items-start gap-3">
              <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${tone}`}><Icon className="h-5 w-5" aria-hidden="true" /></span>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold text-text-muted">{t(`analytics.insights.types.${item.type}`)} · {t(`insightHub.category.${item.category}`)}</p>
                <h3 className="mt-1 break-words text-base font-semibold text-text-primary">{t(item.title_key)}</h3>
              </div>
            </div>
            <p className="text-sm leading-6 text-text-secondary">{description(item)}</p>
            <div className="mt-auto flex flex-wrap items-center justify-between gap-2 border-t border-border-subtle pt-3">
              <span className="inline-flex items-center gap-1 text-xs text-text-muted"><CircleHelp className="h-3.5 w-3.5" />{t("insightHub.source")}: {t(`insightHub.sourceKind.${item.category}`)}</span>
              <Link href={href} className="inline-flex min-h-10 items-center gap-1 rounded-lg px-2 text-sm font-semibold text-primary hover:bg-primary/10">{item.cta_key ? t(item.cta_key) : t("insightHub.openSection")}<ArrowRight className="h-4 w-4" /></Link>
            </div>
          </article>;
        })}
      </div> : null}
      <p className="text-xs leading-5 text-text-muted">{t("insightHub.disclaimer")}</p>
    </> : null}
  </WorkspacePage>;
}
