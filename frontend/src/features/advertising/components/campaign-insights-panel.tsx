"use client";

import { ResponsiveReportTable, type ReportTableColumn } from "@/components/ui/responsive-report-table";
import { CampaignDecisionBadge } from "@/features/advertising/components/campaign-decision-badge";
import { buildCampaignInsightSummary } from "@/features/advertising/lib/decision-support";
import type { EnrichedCampaignPerformance } from "@/features/advertising/lib/decision-support";
import { useI18n } from "@/i18n/provider";
import { formatMoney } from "@/lib/currency";
import type { AdCampaign, CampaignPerformance } from "@/types/advertising";

const DASH = "—";

const formatMetric = (value: number | null, digits = 2) => (value == null || !Number.isFinite(value) ? DASH : value.toFixed(digits));
const formatPercent = (value: number | null) => (value == null || !Number.isFinite(value) ? DASH : `${(value * 100).toFixed(0)}%`);

function CampaignInsightCard({ campaign, currencyCode, reason }: { campaign: EnrichedCampaignPerformance; currencyCode: string; reason: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-bold text-slate-950 dark:text-slate-50">{campaign.campaign_name}</p>
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">{campaign.platform}</p>
        </div>
        <CampaignDecisionBadge label={reason} status={campaign.decision.status} />
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-2 text-sm text-slate-700 dark:text-slate-200">
        <div><dt className="text-xs text-slate-500 dark:text-slate-400">ROAS</dt><dd className="font-bold">{formatMetric(campaign.roasValue, 1)}</dd></div>
        <div><dt className="text-xs text-slate-500 dark:text-slate-400">CPA</dt><dd className="font-bold">{campaign.cpaValue == null ? DASH : formatMoney(campaign.cpaValue, currencyCode)}</dd></div>
        <div><dt className="text-xs text-slate-500 dark:text-slate-400">Spend</dt><dd className="font-bold">{campaign.decision.status === "NO_DATA" ? DASH : formatMoney(campaign.spendValue, currencyCode)}</dd></div>
        <div><dt className="text-xs text-slate-500 dark:text-slate-400">Orders</dt><dd className="font-bold">{campaign.hasMetricData ? campaign.orders : DASH}</dd></div>
      </dl>
    </div>
  );
}

export function CampaignInsightsPanel({ rows, campaigns, currencyCode }: { rows: CampaignPerformance[]; campaigns: AdCampaign[]; currencyCode: string }) {
  const { t } = useI18n();
  const insights = buildCampaignInsightSummary(rows, campaigns);
  const decisionLabels = {
    GOOD: t("advertising.decisionGood"),
    WATCH: t("advertising.decisionWatch"),
    PROBLEM: t("advertising.decisionProblem"),
    NO_DATA: t("advertising.decisionNoData"),
  };

  const comparisonColumns: ReportTableColumn<EnrichedCampaignPerformance>[] = [
    { key: "campaign", label: t("advertising.campaignComparison"), emphasis: true, render: (campaign) =>
      <><span className="block">{campaign.campaign_name}</span><span className="block text-xs font-normal text-text-muted">{t("advertising.manualSource")}</span></> },
    { key: "spend", label: t("advertising.spend"), render: (campaign) => campaign.decision.status === "NO_DATA" ? DASH : formatMoney(campaign.spendValue, currencyCode) },
    { key: "revenue", label: t("advertising.revenue"), render: (campaign) =>
      <><span className="block">{campaign.decision.status === "NO_DATA" ? DASH : formatMoney(campaign.revenueValue, currencyCode)}</span><span className="block text-xs text-text-muted">{t("finance.netProfit")}: {campaign.netProfitValue == null ? DASH : formatMoney(campaign.netProfitValue, currencyCode)}</span></> },
    { key: "orders", label: t("advertising.orders"), render: (campaign) =>
      <><span className="block">{campaign.hasMetricData ? campaign.orders : DASH}</span><span className="block text-xs text-text-muted">{t("advertising.leads")}: {campaign.hasMetricData ? campaign.leads : DASH} · {t("advertising.messages")}: {campaign.hasMetricData ? campaign.messages : DASH}</span></> },
    { key: "efficiency", label: "ROAS / CPA / CPL", render: (campaign) =>
      <><span className="block">ROAS: {formatMetric(campaign.roasValue, 1)}</span><details className="mt-1 text-xs"><summary className="cursor-pointer text-primary">{t("advertising.moreMetrics")}</summary><dl className="mt-1 grid gap-1"><div>CPA: {campaign.cpaValue == null ? DASH : formatMoney(campaign.cpaValue, currencyCode)}</div><div>CPL: {campaign.cplValue == null ? DASH : formatMoney(campaign.cplValue, currencyCode)}</div><div>CR: {formatPercent(campaign.conversionRateValue)}</div></dl></details></> },
    { key: "decision", label: t("advertising.decisionStatus"), render: (campaign) => <CampaignDecisionBadge label={decisionLabels[campaign.decision.status]} status={campaign.decision.status} /> },
  ];

  return (
    <section className="grid w-full max-w-full min-w-0 gap-4 overflow-hidden rounded-2xl bg-white p-4 shadow-sm dark:bg-slate-950" data-advertising-insights="campaign-comparison-decision-support" data-decision-statuses="GOOD WATCH PROBLEM NO_DATA">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600 dark:text-blue-300">{t("advertising.insightsEyebrow")}</p>
        <h2 className="mt-1 text-xl font-black text-slate-950 dark:text-slate-50">{t("advertising.insightsTitle")}</h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{t("advertising.insightsSubtitle")}</p>
      </div>

      <div className="grid gap-3 rounded-2xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-950 dark:border-blue-900 dark:bg-blue-950/40 dark:text-blue-100 md:grid-cols-2">
        <p>{t("advertising.manualImportInsightSource")}</p>
        <p>{t("advertising.metaFutureWorkInsight")}</p>
        <p>{t("advertising.noMisleadingInsight")}</p>
        <p>{t("advertising.stagingBlockedInsight")}</p>
        <p>{t("advertising.noDataVisibilityHint")}</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <div className="rounded-xl border border-slate-200 p-3 text-sm dark:border-slate-800"><p className="font-bold text-slate-950 dark:text-slate-50">ROAS</p><p className="mt-1 text-slate-600 dark:text-slate-300">{t("advertising.roasShortExplanation")}</p></div>
        <div className="rounded-xl border border-slate-200 p-3 text-sm dark:border-slate-800"><p className="font-bold text-slate-950 dark:text-slate-50">CPA</p><p className="mt-1 text-slate-600 dark:text-slate-300">{t("advertising.cpaShortExplanation")}</p></div>
        <div className="rounded-xl border border-slate-200 p-3 text-sm dark:border-slate-800"><p className="font-bold text-slate-950 dark:text-slate-50">CPL</p><p className="mt-1 text-slate-600 dark:text-slate-300">{t("advertising.cplShortExplanation")}</p></div>
        <div className="rounded-xl border border-slate-200 p-3 text-sm dark:border-slate-800"><p className="font-bold text-slate-950 dark:text-slate-50">Conversion Rate</p><p className="mt-1 text-slate-600 dark:text-slate-300">{t("advertising.conversionRateShortExplanation")}</p></div>
        <div className="rounded-xl border border-slate-200 p-3 text-sm dark:border-slate-800"><p className="font-bold text-slate-950 dark:text-slate-50">Cost per Message</p><p className="mt-1 text-slate-600 dark:text-slate-300">{t("advertising.costPerMessageShortExplanation")}</p></div>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="rounded-2xl bg-slate-50 p-4 dark:bg-slate-900">
          <h3 className="font-black text-slate-950 dark:text-slate-50">{t("advertising.topCampaigns")}</h3>
          <div className="mt-3 grid gap-3">
            {insights.topCampaigns.length > 0 ? insights.topCampaigns.map((campaign) => <CampaignInsightCard key={`top-${campaign.campaign_id}`} campaign={campaign} currencyCode={currencyCode} reason={decisionLabels[campaign.decision.status]} />) : <p className="rounded-xl border border-dashed border-slate-300 p-4 text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">{t("advertising.noCampaignInsights")}</p>}
          </div>
        </div>
        <div className="rounded-2xl bg-slate-50 p-4 dark:bg-slate-900">
          <h3 className="font-black text-slate-950 dark:text-slate-50">{t("advertising.campaignsNeedingAttention")}</h3>
          <div className="mt-3 grid gap-3">
            {insights.campaignsNeedingAttention.length > 0 ? insights.campaignsNeedingAttention.map((campaign) => <CampaignInsightCard key={`attention-${campaign.campaign_id}`} campaign={campaign} currencyCode={currencyCode} reason={t(campaign.decision.reasonKey)} />) : <p className="rounded-xl border border-dashed border-slate-300 p-4 text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">{t("advertising.noCampaignInsights")}</p>}
          </div>
        </div>
      </div>

      <ResponsiveReportTable rows={insights.rows} columns={comparisonColumns} rowKey={(campaign) => campaign.campaign_id} wide />
    </section>
  );
}
