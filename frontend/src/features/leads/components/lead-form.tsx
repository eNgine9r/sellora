"use client";

import { FormEvent, useState } from "react";
<<<<<<< HEAD
import { buildLeadCreatePayload } from "@/lib/payload-builders";
import { LeadCreatePayload } from "@/services/crm";
import { LeadSource } from "@/types/crm";
=======
import { useI18n } from "@/i18n/provider";
import { buildLeadCreatePayload } from "@/lib/payload-builders";
import { LeadCreatePayload } from "@/services/crm";
import { LeadSource } from "@/types/crm";
import { AdCampaign } from "@/types/advertising";
>>>>>>> origin/codex/2026-07-01-create-initial-sellora-repository-structure

export type LeadFormValues = {
  name: string;
  phone?: string;
  instagram_username?: string;
  instagram_profile_url?: string;
  lead_source_id?: string;
<<<<<<< HEAD
=======
  campaign_id?: string;
>>>>>>> origin/codex/2026-07-01-create-initial-sellora-repository-structure
  notes?: string;
  assigned_user_id?: string;
  expected_revenue?: string;
};

export function LeadForm({
  leadSources,
<<<<<<< HEAD
=======
  campaigns = [],
>>>>>>> origin/codex/2026-07-01-create-initial-sellora-repository-structure
  onSubmit,
  isSubmitting = false,
  submitError,
}: {
  leadSources: LeadSource[];
<<<<<<< HEAD
=======
  campaigns?: AdCampaign[];
>>>>>>> origin/codex/2026-07-01-create-initial-sellora-repository-structure
  onSubmit: (payload: LeadCreatePayload) => Promise<void> | void;
  isSubmitting?: boolean;
  submitError?: string | null;
}) {
<<<<<<< HEAD
=======
  const { t } = useI18n();
>>>>>>> origin/codex/2026-07-01-create-initial-sellora-repository-structure
  const [values, setValues] = useState<LeadFormValues>({ name: "" });
  const [validationError, setValidationError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = buildLeadCreatePayload(values);
    if (!payload.name) {
      setValidationError("Lead name is required.");
      return;
    }

    setValidationError(null);
    await onSubmit(payload);
  }

  return (
    <form className="grid gap-4" onSubmit={submit}>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
        Name
        <input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" required value={values.name} onChange={(event) => setValues({ ...values, name: event.target.value })} />
      </label>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
        Phone
        <input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" value={values.phone ?? ""} onChange={(event) => setValues({ ...values, phone: event.target.value })} />
      </label>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
        Instagram username
        <input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" value={values.instagram_username ?? ""} onChange={(event) => setValues({ ...values, instagram_username: event.target.value })} />
      </label>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
        Instagram profile URL
        <input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" value={values.instagram_profile_url ?? ""} onChange={(event) => setValues({ ...values, instagram_profile_url: event.target.value })} />
      </label>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
        Source
        <select className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" value={values.lead_source_id ?? ""} onChange={(event) => setValues({ ...values, lead_source_id: event.target.value })}>
          <option value="">No source / Manual</option>
          {leadSources.map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}
        </select>
      </label>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
<<<<<<< HEAD
=======
        {t("leads.campaignField")}
        <span className="text-xs font-normal text-slate-500">{t("leads.campaignHelp")}</span>
        <select className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" value={values.campaign_id ?? ""} onChange={(event) => setValues({ ...values, campaign_id: event.target.value })}>
          <option value="">{t("orders.campaignNotSet")}</option>
          {campaigns.map((campaign) => <option key={campaign.id} value={campaign.id}>{campaign.name} · {campaign.platform}</option>)}
        </select>
      </label>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
>>>>>>> origin/codex/2026-07-01-create-initial-sellora-repository-structure
        Expected revenue
        <input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" min="0" step="0.01" type="number" value={values.expected_revenue ?? ""} onChange={(event) => setValues({ ...values, expected_revenue: event.target.value })} />
      </label>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
        Notes
        <textarea className="min-h-24 min-w-0 rounded-md border border-slate-300 px-3 py-2" value={values.notes ?? ""} onChange={(event) => setValues({ ...values, notes: event.target.value })} />
      </label>
      {validationError ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">{validationError}</p> : null}
      {submitError ? <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700">{submitError}</p> : null}
      <button className="min-h-11 rounded-md bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Creating…" : "Create lead"}
      </button>
    </form>
  );
}
