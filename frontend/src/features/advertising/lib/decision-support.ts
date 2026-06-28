import type { CampaignPerformance } from "@/types/advertising";

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
};

export type CampaignInsightSummary = {
  rows: EnrichedCampaignPerformance[];
  topCampaigns: EnrichedCampaignPerformance[];
  campaignsNeedingAttention: EnrichedCampaignPerformance[];
  averageCpa: number | null;
};

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

export const getCampaignDecision = (
  row: CampaignPerformance,
  averageCpa: number | null,
): CampaignDecision => {
  const spend = toNumber(row.spend);
  const revenue = toNumber(row.revenue);
  const orders = Number.isFinite(row.orders) ? row.orders : 0;
  const leads = Number.isFinite(row.leads) ? row.leads : 0;
  const roas = parseOptionalMetric(row.roas) ?? safeDivide(revenue, spend);
  const cpa = parseOptionalMetric(row.cpa) ?? safeDivide(spend, orders);

  if (spend <= 0) return { status: "NO_DATA", reasonKey: "advertising.decisionNoDataMessage" };
  if (spend > 0 && orders === 0) return { status: "PROBLEM", reasonKey: "advertising.decisionProblemSpendNoOrders" };
  if (leads > 0 && orders === 0) return { status: "WATCH", reasonKey: "advertising.decisionWatchLeadsNoOrders" };
  if (roas != null && roas >= 4) return { status: "GOOD", reasonKey: "advertising.decisionGoodMessage" };
  if (averageCpa != null && cpa != null && cpa > averageCpa * 1.25) {
    return { status: "WATCH", reasonKey: "advertising.decisionWatchHighCpa" };
  }
  return { status: "WATCH", reasonKey: "advertising.decisionDefaultWatch" };
};

export const buildCampaignInsightSummary = (rows: CampaignPerformance[]): CampaignInsightSummary => {
  const cpaValues = rows
    .map((row) => parseOptionalMetric(row.cpa) ?? safeDivide(toNumber(row.spend), row.orders))
    .filter((value): value is number => value != null && Number.isFinite(value));
  const averageCpa = cpaValues.length > 0 ? cpaValues.reduce((sum, value) => sum + value, 0) / cpaValues.length : null;

  const enriched = rows.map((row) => {
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
