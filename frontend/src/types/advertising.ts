export type AdCampaign = { id: string; workspace_id: string; name: string; platform: string; status: string; objective: string; budget_type: string; daily_budget?: string | null; total_budget?: string | null; start_date?: string | null; end_date?: string | null; notes?: string | null };
export type AdMetric = { source_type?: string | null; provider_controlled_fields?: string[]; id: string; workspace_id: string; campaign_id: string; metric_date: string; spend: string; impressions: number; reach: number; clicks: number; messages: number; leads: number; orders: number; revenue: string; net_profit?: string | null; cpa?: string | null; cpl?: string | null; cpc?: string | null; cpm?: string | null; ctr?: string | null; roas?: string | null; roi?: string | null };
export type AdvertisingSummary = { total_spend: string; total_impressions: number; total_reach: number; total_clicks: number; total_messages: number; total_leads: number; total_orders: number; total_revenue: string; total_net_profit?: string | null; average_cpa?: string | null; average_cpl?: string | null; average_cpc?: string | null; average_cpm?: string | null; average_ctr?: string | null; roas?: string | null; roi?: string | null };
export type CampaignPerformance = { campaign_id: string; campaign_name: string; platform: string; status: string; spend: string; revenue: string; net_profit?: string | null; orders: number; leads: number; messages: number; cpa?: string | null; cpl?: string | null; roas?: string | null; roi?: string | null };
export type AdvertisingTrendPoint = { date: string; spend: string; revenue: string; net_profit?: string | null; orders: number; leads: number; cpa?: string | null; roas?: string | null };
export type AdCampaignCreate = { name: string; platform: string; status: string; objective: string; budget_type: string; daily_budget: number | null; total_budget: number | null; start_date: string | null; end_date: string | null; notes: string | null };
export type AdMetricCreate = { campaign_id: string; metric_date: string; spend: number; impressions: number; reach: number; clicks: number; messages: number; leads: number; orders: number; revenue: number; net_profit: number };

export interface CrmAttributionTotals {
  placed_orders: number; placed_revenue: string;
  active_orders: number; active_revenue: string;
  cancelled_orders: number; returned_refunded_orders: number;
  fulfilled_orders: number; fulfilled_revenue: string;
  paid_fulfilled_orders: number; paid_fulfilled_revenue: string;
  spend: string; metric_declared_orders: number; metric_declared_revenue: string;
  crm_period_revenue_to_spend: string | null; cost_per_fulfilled_order: string | null;
}
export interface CrmAttributionCampaign extends CrmAttributionTotals {
  campaign_id: string; campaign_name: string; campaign_status: string;
}
export interface CrmAttributionReport {
  start_date: string; end_date: string;
  date_basis: "order_created_at_utc"; source: "crm_manual_campaign_link"; state_basis: "current_state";
  totals: CrmAttributionTotals; attributed_orders: number; unattributed_orders: number;
  attribution_coverage_percent: string | null; unattributed: CrmAttributionTotals;
  campaigns: CrmAttributionCampaign[];
}
