"use client";

import { FormEvent, useState } from "react";
import { buildAdCampaignCreatePayload } from "@/lib/payload-builders";
import { AdCampaignCreate } from "@/types/advertising";

const PLATFORMS = ["META", "INSTAGRAM", "FACEBOOK", "TIKTOK", "GOOGLE", "TELEGRAM", "OTHER"];
const STATUSES = ["ACTIVE", "PAUSED", "COMPLETED", "ARCHIVED"];
const OBJECTIVES = ["MESSAGES", "SALES", "TRAFFIC", "AWARENESS", "FOLLOWERS", "OTHER"];
const BUDGET_TYPES = ["DAILY", "LIFETIME", "MANUAL"];

export function CampaignForm({ onSubmit }: { onSubmit?: (payload: AdCampaignCreate) => void }) {
  const [values, setValues] = useState<Record<string, string>>({ name: "", platform: "INSTAGRAM", status: "ACTIVE", objective: "MESSAGES", budget_type: "MANUAL" });
  const [validationError, setValidationError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = buildAdCampaignCreatePayload(values);
    if (!payload.name) {
      setValidationError("Campaign name is required.");
      return;
    }
    setValidationError(null);
    onSubmit?.(payload);
  }

  return (
    <form className="grid w-full min-w-0 max-w-full gap-3 overflow-hidden rounded-2xl bg-white p-4 shadow-sm" onSubmit={submit}>
      <h2 className="text-lg font-semibold">Create Campaign</h2>
      <input className="w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" placeholder="Campaign name" required value={values.name ?? ""} onChange={(event) => setValues({ ...values, name: event.target.value })} />
      <div className="grid min-w-0 gap-3 sm:grid-cols-2">
        <select className="w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" value={values.platform} onChange={(event) => setValues({ ...values, platform: event.target.value })}>{PLATFORMS.map((item) => <option key={item} value={item}>{item}</option>)}</select>
        <select className="w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" value={values.status} onChange={(event) => setValues({ ...values, status: event.target.value })}>{STATUSES.map((item) => <option key={item} value={item}>{item}</option>)}</select>
        <select className="w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" value={values.objective} onChange={(event) => setValues({ ...values, objective: event.target.value })}>{OBJECTIVES.map((item) => <option key={item} value={item}>{item}</option>)}</select>
        <select className="w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" value={values.budget_type} onChange={(event) => setValues({ ...values, budget_type: event.target.value })}>{BUDGET_TYPES.map((item) => <option key={item} value={item}>{item}</option>)}</select>
      </div>
      <div className="grid min-w-0 gap-3 sm:grid-cols-2">
        <input className="w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder="Daily budget" value={values.daily_budget ?? ""} onChange={(event) => setValues({ ...values, daily_budget: event.target.value })} />
        <input className="w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" placeholder="Total budget" value={values.total_budget ?? ""} onChange={(event) => setValues({ ...values, total_budget: event.target.value })} />
        <input className="sellora-date-input w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" type="date" value={values.start_date ?? ""} onChange={(event) => setValues({ ...values, start_date: event.target.value })} />
        <input className="sellora-date-input w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" type="date" value={values.end_date ?? ""} onChange={(event) => setValues({ ...values, end_date: event.target.value })} />
      </div>
      <textarea className="w-full min-w-0 max-w-full rounded-md border border-slate-300 px-3 py-2" placeholder="Notes" value={values.notes ?? ""} onChange={(event) => setValues({ ...values, notes: event.target.value })} />
      {validationError ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">{validationError}</p> : null}
      <button className="min-h-11 w-full min-w-0 max-w-full rounded-md bg-blue-600 px-4 py-2 font-semibold text-white" type="submit">Create campaign</button>
    </form>
  );
}
