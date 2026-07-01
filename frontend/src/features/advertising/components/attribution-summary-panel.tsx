"use client";

import { formatMoney } from "@/lib/currency";
import type { AdCampaign } from "@/types/advertising";
import type { Order } from "@/types/orders";

function inPeriod(order: Order, startDate?: string, endDate?: string) {
  const created = order.created_at.slice(0, 10);
  if (startDate && created < startDate) return false;
  if (endDate && created > endDate) return false;
  return true;
}

export function AttributionSummaryPanel({ campaigns, orders, currencyCode, startDate, endDate }: { campaigns: AdCampaign[]; orders: Order[]; currencyCode: string; startDate?: string; endDate?: string }) {
  const campaignIds = new Set(campaigns.map((campaign) => campaign.id));
  const periodOrders = orders.filter((order) => inPeriod(order, startDate, endDate));
  const attributedOrders = periodOrders.filter((order) => order.campaign_id && campaignIds.has(order.campaign_id));
  const unattributedOrders = periodOrders.length - attributedOrders.length;
  const attributedRevenue = attributedOrders.reduce((sum, order) => sum + Number(order.revenue ?? 0), 0);
  const attributedProfit = attributedOrders.reduce((sum, order) => sum + Number(order.net_profit ?? 0), 0);
  const linkedCampaigns = new Set(attributedOrders.map((order) => order.campaign_id)).size;

  return (
    <section className="grid gap-4 rounded-2xl bg-white p-4 shadow-sm dark:bg-slate-950" data-advertising-attribution="manual-campaign-attribution optional-lead-order-campaign-link no-pilot-ready-claim">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-600">Manual attribution MVP</p>
        <h2 className="mt-1 text-xl font-black text-slate-950 dark:text-slate-50">Атрибуція замовлень</h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Показує лише замовлення, де рекламну кампанію було вказано вручну. Замовлення без кампанії залишаються валідними та не вважаються помилкою.</p>
        <p className="mt-1 text-xs font-semibold text-slate-500 dark:text-slate-400">Meta Ads API attribution is future work; current manual attribution is workspace-scoped and based on existing order/campaign access.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <div className="rounded-xl border border-indigo-100 bg-indigo-50 p-3 text-sm text-indigo-950"><span>Campaign-linked Orders</span><strong className="block text-xl">{attributedOrders.length}</strong></div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-800"><span>Unattributed Orders</span><strong className="block text-xl">{unattributedOrders}</strong></div>
        <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-3 text-sm text-emerald-950"><span>Attributed Revenue</span><strong className="block text-xl">{formatMoney(attributedRevenue, currencyCode)}</strong></div>
        <div className="rounded-xl border border-violet-100 bg-violet-50 p-3 text-sm text-violet-950"><span>Attributed Net Profit</span><strong className="block text-xl">{formatMoney(attributedProfit, currencyCode)}</strong></div>
        <div className="rounded-xl border border-orange-100 bg-orange-50 p-3 text-sm text-orange-950"><span>Linked Campaigns</span><strong className="block text-xl">{linkedCampaigns}</strong></div>
      </div>
    </section>
  );
}
