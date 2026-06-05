"use client";

import { FormEvent, useState } from "react";
import { buildAdMetricCreatePayload } from "@/lib/payload-builders";
import { AdCampaign, AdMetricCreate } from "@/types/advertising";

export function AdMetricForm({ campaigns = [], onSubmit }: { campaigns?: AdCampaign[]; onSubmit?: (payload: AdMetricCreate) => void }) {
  const [values, setValues] = useState<Record<string, string>>({ campaign_id: "", metric_date: new Date().toISOString().slice(0, 10) });
  const [validationError, setValidationError] = useState<string | null>(null);
  const hasCampaigns = campaigns.length > 0;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!hasCampaigns) {
      setValidationError("Create an advertising campaign first.");
      return;
    }
    const payload = buildAdMetricCreatePayload(values);
    if (!payload.campaign_id) {
      setValidationError("Please select a campaign.");
      return;
    }
    if (!payload.metric_date) {
      setValidationError("Metric date is required.");
      return;
    }
    setValidationError(null);
    onSubmit?.(payload);
  }

  return (
    <form className="grid w-full min-w-0 max-w-full gap-3 overflow-hidden rounded-2xl bg-white p-4 shadow-sm" onSubmit={submit} noValidate>
      <h2 className="text-lg font-semibold">Add Daily Metrics</h2>
      {!hasCampaigns ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">Create an advertising campaign first.</p> : null}
      <select className="min-h-11 w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" value={values.campaign_id} disabled={!hasCampaigns} onChange={(event) => setValues({ ...values, campaign_id: event.target.value })}>
        <option value="">Select campaign</option>
        {campaigns.map((campaign) => <option key={campaign.id} value={campaign.id}>{campaign.name}</option>)}
      </select>
      <input className="min-h-11 w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" type="date" value={values.metric_date} onChange={(event) => setValues({ ...values, metric_date: event.target.value })} />
      <div className="grid min-w-0 gap-3 sm:grid-cols-3">
        {["spend", "impressions", "reach", "clicks", "messages", "leads", "orders", "revenue", "net_profit"].map((field) => <input key={field} className="min-h-11 w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder={field.replace("_", " ")} value={values[field] ?? ""} onChange={(event) => setValues({ ...values, [field]: event.target.value })} />)}
      </div>
      {validationError ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">{validationError}</p> : null}
      <button className="min-h-11 w-full min-w-0 max-w-full rounded-md bg-blue-600 px-4 py-2 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60" disabled={!hasCampaigns} type="submit">Add metrics</button>
    </form>
  );
}
