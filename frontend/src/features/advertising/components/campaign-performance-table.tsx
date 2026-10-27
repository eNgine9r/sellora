"use client";

import { ResponsiveReportTable, type ReportTableColumn } from "@/components/ui/responsive-report-table";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import type { CampaignPerformance } from "@/types/advertising";

export function CampaignPerformanceTable({
  rows, currencyCode = "UAH",
}: {
  rows: CampaignPerformance[]; currencyCode?: string;
}) {
  const { t } = useI18n();
  const columns: ReportTableColumn<CampaignPerformance>[] = [
    {
      key: "campaign", label: t("advertising.campaignComparison"), emphasis: true,
      render: row => <div className="min-w-0"><span className="block min-w-0 truncate font-semibold" title={row.campaign_name}>{row.campaign_name}</span><span className="block text-xs font-normal text-text-muted">{row.platform}</span></div>,
    },
    { key: "spend", label: t("adsDashboard.spend"), render: row => <span className="tabular-nums font-semibold">{formatMoney(row.spend, currencyCode)}</span> },
    { key: "messages", label: t("adsDashboard.messages"), render: row => <span className="tabular-nums">{row.messages}</span> },
    { key: "costMessage", label: t("adsDashboard.costPerMessage"), render: row => {
      const spend = Number(row.spend);
      return <span className="tabular-nums">{row.messages > 0 && Number.isFinite(spend) ? formatMoney(spend / row.messages, currencyCode) : "—"}</span>;
    } },
    { key: "orders", label: t("adsDashboard.orders"), render: row => <div><span className="block tabular-nums">{row.orders}</span><span className="block text-xs text-text-muted">{t("adsDashboard.crmLabel")}</span></div> },
  ];
  return (
    <section className="w-full min-w-0 max-w-full rounded-2xl border border-border-subtle bg-surface-1 p-4 shadow-sm" data-advertising-campaign-performance>
      <h3 className="mb-3 text-base font-bold text-text-primary">{t("adsDashboard.campaignsTitle")}</h3>
      <ResponsiveReportTable rows={rows} columns={columns} rowKey={row => row.campaign_id} wide />
    </section>
  );
}
