"use client";

import { RowActionButtons } from "@/components/ui/row-action-buttons";
import { useI18n } from "@/i18n/provider";
import { AdMetric } from "@/types/advertising";
import { MetricValue } from "./metric-value";

export function AdMetricTable({ metrics, onEdit, onDelete }: { metrics: AdMetric[]; onEdit?: (metric: AdMetric) => void; onDelete?: (metric: AdMetric) => void }) {
  const { t } = useI18n();

  function extraMetrics(metric: AdMetric) {
    return (
      <details className="mt-1 text-xs text-text-secondary">
        <summary className="cursor-pointer text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring">{t("advertising.moreMetrics")}</summary>
        {metric.exchange_rate_source === "NBU" ? <p className="mt-2 break-words">{t("advertising.fxEvidence", { amount: metric.original_spend ?? "—", currency: metric.original_currency ?? "—", rate: metric.exchange_rate ?? "—", date: metric.exchange_rate_date ?? "—" })}</p> : null}
        <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 rounded-lg bg-surface-2 p-2">
          <span>{t("advertising.impressions")}: {metric.impressions}</span>
          <span>{t("advertising.reach")}: {metric.reach}</span>
          <span>{t("advertising.clicks")}: {metric.clicks}</span>
          <span>{t("advertising.cpc")}: <MetricValue value={metric.cpc} /></span>
          <span>{t("advertising.cpm")}: <MetricValue value={metric.cpm} /></span>
          <span>{t("advertising.ctr")}: <MetricValue value={metric.ctr} suffix="%" /></span>
          <span>{t("advertising.cpl")}: <MetricValue value={metric.cpl} /></span>
        </div>
      </details>
    );
  }

  function rowActions(metric: AdMetric) {
    return (
      <RowActionButtons
        entityLabel={metric.metric_date}
        editLabel={t("advertising.editMetric")}
        archiveLabel={t("actions.delete")}
        destructiveIcon="delete"
        onEdit={onEdit ? () => onEdit(metric) : undefined}
        onArchive={onDelete ? () => onDelete(metric) : undefined}
      />
    );
  }

  return (
    <section className="sellora-adaptive-list w-full min-w-0 max-w-full rounded-2xl border border-border-subtle bg-surface-1 p-3 shadow-sm">
      <h2 className="text-lg font-semibold text-text-primary">{t("advertising.dailyMetrics")}</h2>
      <div className="sellora-adaptive-table mt-3 w-full min-w-0">
        <table className="w-full table-fixed text-left text-sm">
          <colgroup>
            <col style={{ width: "23%" }} />
            <col style={{ width: "13%" }} />
            <col style={{ width: "21%" }} />
            <col style={{ width: "13%" }} />
            <col style={{ width: "18%" }} />
            <col style={{ width: "12%" }} />
          </colgroup>
          <thead className="text-xs uppercase tracking-wide text-text-muted">
            <tr className="border-b border-border-subtle">
              <th className="px-2 py-3">{t("advertising.metricDate")}</th>
              <th className="px-2 py-3">{t("advertising.spend")}</th>
              <th className="px-2 py-3">{t("advertising.messages")} / {t("advertising.leads")}</th>
              <th className="px-2 py-3">{t("advertising.revenue")}</th>
              <th className="px-2 py-3">{t("advertising.netProfit")}</th>
              <th className="px-2 py-3 text-right">{t("tables.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((metric) => (
              <tr key={metric.id} className="border-b border-border-subtle last:border-0 align-top">
                <td className="min-w-0 px-2 py-3">
                  <span className="font-semibold text-text-primary">{metric.metric_date}</span>
                  {extraMetrics(metric)}
                </td>
                <td className="px-2 py-3 text-text-secondary">{metric.spend}</td>
                <td className="px-2 py-3 text-xs text-text-secondary">
                  <span className="block">{t("advertising.messages")}: {metric.messages}</span>
                  <span className="block">{t("advertising.leads")}: {metric.leads}</span>
                  <span className="block">{t("advertising.orders")}: {metric.orders}</span>
                </td>
                <td className="px-2 py-3 text-text-secondary">
                  <span className="block">{metric.revenue}</span>
                  <span className="block text-xs">ROAS: <MetricValue value={metric.roas} /></span>
                  <span className="block text-xs">CPA: <MetricValue value={metric.cpa} /></span>
                </td>
                <td className="px-2 py-3 text-text-secondary">
                  <MetricValue value={metric.net_profit} />
                  <span className="block text-xs">{t("advertising.roi")}: <MetricValue value={metric.roi} suffix="%" /></span>
                </td>
                <td className="px-1 py-2">{rowActions(metric)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="sellora-adaptive-cards mt-3 grid gap-3">
        {metrics.map((metric) => (
          <article key={metric.id} className="min-w-0 rounded-xl border border-border-subtle bg-surface-2 p-3">
            <div className="flex justify-between gap-3">
              <div className="min-w-0"><h3 className="font-semibold text-text-primary">{metric.metric_date}</h3><p className="mt-1 text-sm text-text-secondary">{t("advertising.spend")}: {metric.spend}</p></div>
              {rowActions(metric)}
            </div>
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-text-secondary">
              <span>{t("advertising.messages")}: {metric.messages}</span>
              <span>{t("advertising.leads")}: {metric.leads}</span>
              <span>{t("advertising.orders")}: {metric.orders}</span>
              <span>{t("advertising.revenue")}: {metric.revenue}</span>
              <span>ROAS: <MetricValue value={metric.roas} /></span>
              <span>CPA: <MetricValue value={metric.cpa} /></span>
              <span>{t("advertising.netProfit")}: <MetricValue value={metric.net_profit} /></span>
              <span>{t("advertising.roi")}: <MetricValue value={metric.roi} suffix="%" /></span>
            </div>
            {extraMetrics(metric)}
          </article>
        ))}
      </div>
    </section>
  );
}
// Regression compatibility: Edit metric; Delete metric; Read-only.
