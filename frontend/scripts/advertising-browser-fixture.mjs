// Synthetic advertising responses mirror CrmAttributionResponse and existing
// advertising contracts. Unknown routes still fail in the canonical fixture.
export function createAdvertisingFixture({ workspaceId }) {
  const campaignId = "12121212-1212-4212-8212-121212121212";
  const archivedId = "13131313-1313-4313-8313-131313131313";
  const totals = {
    placed_orders: 0, placed_revenue: "0", active_orders: 0, active_revenue: "0",
    cancelled_orders: 0, returned_refunded_orders: 0, fulfilled_orders: 0,
    fulfilled_revenue: "0", paid_fulfilled_orders: 0, paid_fulfilled_revenue: "0",
    spend: "0", metric_declared_orders: 0, metric_declared_revenue: "0",
    crm_period_revenue_to_spend: null, cost_per_fulfilled_order: null,
  };
  const state = { mode: "populated", requests: [], hold: false, release: null };
  return { state, async handle({ key, requestWorkspace, respond, url }) {
    if (!key.startsWith("GET /api/v1/advertising/")) return false;
    if (requestWorkspace !== workspaceId) throw new Error("Advertising fixture workspace mismatch");
    state.requests.push({ key, start: url.searchParams.get("start_date"), end: url.searchParams.get("end_date"), workspace: requestWorkspace });
    const send = async (data, status = 200) => { await respond(data, status); return true; };
    if (key === "GET /api/v1/advertising/crm-attribution") {
      if (state.hold) await new Promise((resolve) => { state.release = resolve; });
      if (state.mode === "error") return send({ detail: "Synthetic report failure" }, 503);
      const empty = state.mode === "empty";
      const narrow = url.searchParams.get("start_date") === "2026-10-01" && url.searchParams.get("end_date") === "2026-10-02";
      const report = {
        start_date: url.searchParams.get("start_date") || "2026-09-19",
        end_date: url.searchParams.get("end_date") || "2026-10-19",
        date_basis: "order_created_at_utc", source: "crm_manual_campaign_link", state_basis: "current_state",
        totals: empty ? totals : { ...totals, placed_orders: 5, placed_revenue: "1400", active_orders: 3, active_revenue: "1200", cancelled_orders: 1, returned_refunded_orders: 1, fulfilled_orders: 3, fulfilled_revenue: "1200", paid_fulfilled_orders: 1, paid_fulfilled_revenue: "500", spend: "100", metric_declared_orders: 1, metric_declared_revenue: "150", crm_period_revenue_to_spend: "12.00", cost_per_fulfilled_order: "33.33" },
        attributed_orders: empty ? 0 : 4, unattributed_orders: empty ? 0 : 1,
        attribution_coverage_percent: empty ? null : "80.00",
        unattributed: empty ? totals : { ...totals, placed_orders: 1, placed_revenue: "500", active_orders: 1, active_revenue: "500", fulfilled_orders: 1, fulfilled_revenue: "500" },
        campaigns: empty ? [] : [
          { ...totals, campaign_id: campaignId, campaign_name: "Синтетична реклама", campaign_status: "ACTIVE", placed_orders: 3, placed_revenue: "700", active_orders: 1, active_revenue: "500", cancelled_orders: 1, returned_refunded_orders: 1, fulfilled_orders: 1, fulfilled_revenue: "500", paid_fulfilled_orders: 1, paid_fulfilled_revenue: "500", spend: "100", metric_declared_orders: 1, metric_declared_revenue: "150", crm_period_revenue_to_spend: "5.00", cost_per_fulfilled_order: "100.00" },
          { ...totals, campaign_id: archivedId, campaign_name: "Синтетична історія", campaign_status: "ARCHIVED", placed_orders: 1, placed_revenue: "200", active_orders: 1, active_revenue: "200", fulfilled_orders: 1, fulfilled_revenue: "200" },
        ],
      };
      if (narrow && !empty) {
        report.totals = { ...totals, placed_orders: 2, placed_revenue: "1000", active_orders: 2, active_revenue: "1000", fulfilled_orders: 2, fulfilled_revenue: "1000", paid_fulfilled_orders: 1, paid_fulfilled_revenue: "500", spend: "543.48", metric_declared_orders: 1, metric_declared_revenue: "150", crm_period_revenue_to_spend: "1.84", cost_per_fulfilled_order: "271.74" };
        report.attributed_orders = 1;
        report.attribution_coverage_percent = "50.00";
        report.campaigns = [{ ...report.campaigns[0], placed_orders: 1, placed_revenue: "500", cancelled_orders: 0, returned_refunded_orders: 0, spend: "543.48", crm_period_revenue_to_spend: "0.92", cost_per_fulfilled_order: "543.48" }];
      }
      return send(report);
    }
    if (key === "GET /api/v1/advertising/campaigns") return send([
      { id: campaignId, workspace_id: workspaceId, name: "Синтетична реклама", platform: "INSTAGRAM", status: "ACTIVE", objective: "MESSAGES", budget_type: "MANUAL", daily_budget: null, total_budget: null, start_date: null, end_date: null, notes: null },
    ]);
    if (key === "GET /api/v1/advertising/metrics" || key === "GET /api/v1/advertising/campaign-performance" || key === "GET /api/v1/advertising/trend") return send([]);
    if (key === "GET /api/v1/advertising/summary") return send({ total_spend: "100", total_impressions: 0, total_reach: 0, total_clicks: 0, total_messages: 0, total_leads: 0, total_orders: 1, total_revenue: "150", total_net_profit: null, average_cpa: "100", average_cpl: null, average_cpc: null, average_cpm: null, average_ctr: null, roas: "1.5", roi: null });
    return false;
  } };
}
