import type { AdCampaign, CampaignPerformance } from "@/types/advertising";

export type DecisionStatus = "GOOD" | "WATCH" | "PROBLEM" | "NO_DATA";

export type CampaignDecision = {
  status: DecisionStatus;
  reasonKey: string;
};

export type EnrichedCampaignPerformance = CampaignPerformance & {
  spendValue: number;
  revenueValue: number;
  netProfitValue: number | null;
  roasValue: number | null;
  cpaValue: number | null;
  cplValue: number | null;
  costPerMessageValue: number | null;
  conversionRateValue: number | null;
  decision: CampaignDecision;
  hasMetricData: boolean;
};

export type CampaignInsightSummary = {
  rows: EnrichedCampaignPerformance[];
  topCampaigns: EnrichedCampaignPerformance[];
  campaignsNeedingAttention: EnrichedCampaignPerformance[];
  averageCpa: number | null;
};

const WEAK_CONVERSION_RATE = 0.2;

const toNumber = (value: string | number | null | undefined): number => {
  if (value == null || value === "") return 0;
  const normalized = typeof value === "string" ? Number(value.replace(",", ".")) : Number(value);
  return Number.isFinite(normalized) ? normalized : 0;
};

const safeDivide = (numerator: number, denominator: number): number | null => {
  if (!Number.isFinite(numerator) || !Number.isFinite(denominator) || denominator <= 0) return null;
  return numerator / denominator;
};

const parseOptionalMetric = (value: string | number | null | undefined): number | null => {
  if (value == null || value === "") return null;
  const parsed = toNumber(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const emptyPerformanceRow = (campaign: AdCampaign): CampaignPerformance => ({
  campaign_id: campaign.id,
  campaign_name: campaign.name,
  platform: campaign.platform,
  status: campaign.status,
  spend: "0",
  revenue: "0",
  net_profit: null,
  orders: 0,
  leads: 0,
  messages: 0,
  cpa: null,
  cpl: null,
  roas: null,
  roi: null,
});

export const mergeCampaignsWithPerformance = (
  campaigns: AdCampaign[],
  performanceRows: CampaignPerformance[],
): Array<CampaignPerformance & { hasMetricData?: boolean }> => {
  const rowsByCampaign = new Map(performanceRows.map((row) => [row.campaign_id, row]));
  const merged = campaigns.map((campaign) => {
    const existing = rowsByCampaign.get(campaign.id);
    if (existing) return { ...existing, hasMetricData: true };
    return { ...emptyPerformanceRow(campaign), hasMetricData: false };
  });
  const campaignIds = new Set(campaigns.map((campaign) => campaign.id));
  const orphanPerformanceRows = performanceRows
    .filter((row) => !campaignIds.has(row.campaign_id))
    .map((row) => ({ ...row, hasMetricData: true }));
  return [...merged, ...orphanPerformanceRows];
};

export const getCampaignDecision = (
  row: CampaignPerformance & { hasMetricData?: boolean },
  averageCpa: number | null,
): CampaignDecision => {
  const spend = toNumber(row.spend);
  const revenue = toNumber(row.revenue);
  const orders = Number.isFinite(row.orders) ? row.orders : 0;
  const leads = Number.isFinite(row.leads) ? row.leads : 0;
  const roas = parseOptionalMetric(row.roas) ?? safeDivide(revenue, spend);
  const cpa = parseOptionalMetric(row.cpa) ?? safeDivide(spend, orders);
  const conversionRate = safeDivide(orders, leads);

  // Priority order: 1. NO_DATA, 2. PROBLEM, 3. GOOD, 4. WATCH.
  if (row.hasMetricData === false || spend <= 0) return { status: "NO_DATA", reasonKey: "advertising.decisionNoDataMessage" };
  if (spend > 0 && leads > 0 && orders === 0) return { status: "PROBLEM", reasonKey: "advertising.decisionProblemLeadsNoOrders" };
  if (spend > 0 && orders === 0) return { status: "PROBLEM", reasonKey: "advertising.decisionProblemSpendNoOrders" };
  if (roas != null && roas >= 4 && orders > 0 && revenue > 0) return { status: "GOOD", reasonKey: "advertising.decisionGoodMessage" };
  if (averageCpa != null && cpa != null && cpa > averageCpa * 1.25) {
    return { status: "WATCH", reasonKey: "advertising.decisionWatchHighCpa" };
  }
  if (conversionRate != null && leads > 0 && orders > 0 && conversionRate < WEAK_CONVERSION_RATE) {
    return { status: "WATCH", reasonKey: "advertising.decisionWatchWeakConversion" };
  }
  return { status: "WATCH", reasonKey: "advertising.decisionDefaultWatch" };
};

export const buildCampaignInsightSummary = (
  rows: CampaignPerformance[],
  campaigns: AdCampaign[] = [],
): CampaignInsightSummary => {
  const mergedRows = campaigns.length > 0 ? mergeCampaignsWithPerformance(campaigns, rows) : rows.map((row) => ({ ...row, hasMetricData: true }));
  const cpaValues = mergedRows
    .filter((row) => row.hasMetricData !== false && toNumber(row.spend) > 0 && row.orders > 0)
    .map((row) => parseOptionalMetric(row.cpa) ?? safeDivide(toNumber(row.spend), row.orders))
    .filter((value): value is number => value != null && Number.isFinite(value));
  const averageCpa = cpaValues.length > 0 ? cpaValues.reduce((sum, value) => sum + value, 0) / cpaValues.length : null;

  const enriched = mergedRows.map((row) => {
    const spendValue = toNumber(row.spend);
    const revenueValue = toNumber(row.revenue);
    const netProfitValue = parseOptionalMetric(row.net_profit);
    const roasValue = parseOptionalMetric(row.roas) ?? safeDivide(revenueValue, spendValue);
    const cpaValue = parseOptionalMetric(row.cpa) ?? safeDivide(spendValue, row.orders);
    const cplValue = parseOptionalMetric(row.cpl) ?? safeDivide(spendValue, row.leads);
    const costPerMessageValue = safeDivide(spendValue, row.messages);
    const conversionRateValue = safeDivide(row.orders, row.leads);
    return {
      ...row,
      spendValue,
      revenueValue,
      netProfitValue,
      roasValue,
      cpaValue,
      cplValue,
      costPerMessageValue,
      conversionRateValue,
      hasMetricData: row.hasMetricData !== false,
      decision: getCampaignDecision(row, averageCpa),
    };
  });

  const topCampaigns = [...enriched]
    .filter((row) => row.decision.status !== "NO_DATA")
    .sort((a, b) => (b.roasValue ?? 0) - (a.roasValue ?? 0) || b.revenueValue - a.revenueValue || b.orders - a.orders)
    .slice(0, 3);

  const campaignsNeedingAttention = [...enriched]
    .filter((row) => row.decision.status === "PROBLEM" || row.decision.status === "WATCH")
    .sort((a, b) => {
      const severity = (row: EnrichedCampaignPerformance) => (row.decision.status === "PROBLEM" ? 2 : 1);
      return severity(b) - severity(a) || b.spendValue - a.spendValue || (b.cpaValue ?? 0) - (a.cpaValue ?? 0);
    })
    .slice(0, 3);

  return { rows: enriched, topCampaigns, campaignsNeedingAttention, averageCpa };
};
