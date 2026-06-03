"use client";

import { FormEvent, useState } from "react";
import { buildAdMetricCreatePayload } from "@/lib/payload-builders";
import { AdCampaign, AdMetricCreate } from "@/types/advertising";

export function AdMetricForm({ campaigns = [], onSubmit }: { campaigns?: AdCampaign[]; onSubmit?: (payload: AdMetricCreate) => void }) {
  const [values, setValues] = useState<Record<string, string>>({ campaign_id: "", metric_date: new Date().toISOString().slice(0, 10) });
  const [validationError, setValidationError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = buildAdMetricCreatePayload(values);
    if (!payload.campaign_id) {
      setValidationError("Campaign is required.");
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
    <form className="grid gap-3 rounded-2xl bg-white p-4 shadow-sm" onSubmit={submit}>
      <h2 className="text-lg font-semibold">Add Daily Metrics</h2>
      <select className="rounded-md border border-slate-300 px-3 py-2" required value={values.campaign_id} onChange={(event) => setValues({ ...values, campaign_id: event.target.value })}><option value="">Select campaign</option>{campaigns.map((campaign) => <option key={campaign.id} value={campaign.id}>{campaign.name}</option>)}</select>
      <input className="rounded-md border border-slate-300 px-3 py-2" type="date" value={values.metric_date} onChange={(event) => setValues({ ...values, metric_date: event.target.value })} />
      <div className="grid gap-3 sm:grid-cols-3">
        {["spend", "impressions", "reach", "clicks", "messages", "leads", "orders", "revenue", "net_profit"].map((field) => <input key={field} className="rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder={field.replace("_", " ")} value={values[field] ?? ""} onChange={(event) => setValues({ ...values, [field]: event.target.value })} />)}
      </div>
      {validationError ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">{validationError}</p> : null}
      <button className="rounded-md bg-blue-600 px-4 py-2 font-semibold text-white" type="submit">Add metrics</button>
    </form>
  );
}
