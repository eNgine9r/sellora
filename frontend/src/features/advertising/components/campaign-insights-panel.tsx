"use client";

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

      <div className="sellora-scrollbar max-w-full overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800">
        <table className="w-full min-w-[980px] text-left text-sm text-slate-700 dark:text-slate-200">
          <thead><tr className="border-b bg-slate-50 text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400"><th className="p-3">{t("advertising.campaignComparison")}</th><th>{t("advertising.source")}</th><th>{t("advertising.spend")}</th><th>{t("advertising.messages")}</th><th>{t("advertising.leads")}</th><th>{t("advertising.orders")}</th><th>{t("advertising.revenue")}</th><th>Net Profit</th><th>ROAS</th><th>CPA</th><th>CPL</th><th>Conversion Rate</th><th>{t("advertising.decisionStatus")}</th></tr></thead>
          <tbody>{insights.rows.map((campaign) => <tr key={`comparison-${campaign.campaign_id}`} className="border-b last:border-0 dark:border-slate-800"><td className="p-3 font-bold text-slate-950 dark:text-slate-50">{campaign.campaign_name}</td><td>{t("advertising.manualSource")}</td><td>{campaign.decision.status === "NO_DATA" ? DASH : formatMoney(campaign.spendValue, currencyCode)}</td><td>{campaign.hasMetricData ? campaign.messages : DASH}</td><td>{campaign.hasMetricData ? campaign.leads : DASH}</td><td>{campaign.hasMetricData ? campaign.orders : DASH}</td><td>{campaign.decision.status === "NO_DATA" ? DASH : formatMoney(campaign.revenueValue, currencyCode)}</td><td>{campaign.netProfitValue == null ? DASH : formatMoney(campaign.netProfitValue, currencyCode)}</td><td>{formatMetric(campaign.roasValue, 1)}</td><td>{campaign.cpaValue == null ? DASH : formatMoney(campaign.cpaValue, currencyCode)}</td><td>{campaign.cplValue == null ? DASH : formatMoney(campaign.cplValue, currencyCode)}</td><td>{formatPercent(campaign.conversionRateValue)}</td><td><CampaignDecisionBadge label={decisionLabels[campaign.decision.status]} status={campaign.decision.status} /></td></tr>)}</tbody>
        </table>
      </div>
    </section>
  );
}
