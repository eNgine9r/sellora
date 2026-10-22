"use client";

import { ResponsiveReportTable, type ReportTableColumn } from "@/components/ui/responsive-report-table";
import { useI18n } from "@/i18n/provider";
import type { CampaignPerformance } from "@/types/advertising";
import { MetricValue } from "./metric-value";

export function CampaignPerformanceTable({ rows }: { rows: CampaignPerformance[] }) {
  const { t } = useI18n();
  const columns: ReportTableColumn<CampaignPerformance>[] = [
    { key: "campaign", label: t("advertising.campaign"), emphasis: true, render: (row) =>
      <><span className="block">{row.campaign_name}</span><span className="block text-xs font-normal text-text-muted">{row.platform}</span></> },
    { key: "spend", label: t("advertising.spend"), render: (row) => row.spend },
    { key: "revenue", label: t("advertising.revenue"), render: (row) =>
      <><span className="block">{row.revenue}</span><span className="block text-xs text-text-muted">{t("finance.netProfit")}: <MetricValue value={row.net_profit} /></span></> },
    { key: "results", label: t("advertising.orders"), render: (row) =>
      <><span className="block">{row.orders}</span><span className="block text-xs text-text-muted">{t("advertising.leads")}: {row.leads} · {t("advertising.messages")}: {row.messages}</span></> },
    { key: "cost", label: "CPA / CPL", render: (row) =>
      <><span className="block">CPA: <MetricValue value={row.cpa} /></span><span className="block text-xs">CPL: <MetricValue value={row.cpl} /></span></> },
    { key: "roas", label: "ROAS / ROI", render: (row) =>
      <><span className="block">ROAS: <MetricValue value={row.roas} /></span><span className="block text-xs">ROI: <MetricValue value={row.roi} suffix="%" /></span></> },
  ];
  return (
    <section className="w-full min-w-0 max-w-full rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm">
      <h2 className="mb-3 text-lg font-semibold text-text-primary">{t("advertising.performanceTitle")}</h2>
      <ResponsiveReportTable rows={rows} columns={columns} rowKey={(row) => row.campaign_id} wide />
    </section>
  );
}
