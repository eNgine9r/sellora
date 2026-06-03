"use client";

import { FormEvent, useState } from "react";
import { buildLeadCreatePayload } from "@/lib/payload-builders";
import { LeadCreatePayload } from "@/services/crm";
import { LeadSource } from "@/types/crm";

export type LeadFormValues = {
  name: string;
  phone?: string;
  instagram_username?: string;
  instagram_profile_url?: string;
  lead_source_id?: string;
  notes?: string;
  assigned_user_id?: string;
  expected_revenue?: string;
};

export function LeadForm({
  leadSources,
  onSubmit,
  isSubmitting = false,
  submitError,
}: {
  leadSources: LeadSource[];
  onSubmit: (payload: LeadCreatePayload) => Promise<void> | void;
  isSubmitting?: boolean;
  submitError?: string | null;
}) {
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
        <input className="min-h-11 rounded-md border border-slate-300 px-3 py-2" required value={values.name} onChange={(event) => setValues({ ...values, name: event.target.value })} />
      </label>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
        Phone
        <input className="min-h-11 rounded-md border border-slate-300 px-3 py-2" value={values.phone ?? ""} onChange={(event) => setValues({ ...values, phone: event.target.value })} />
      </label>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
        Instagram username
        <input className="min-h-11 rounded-md border border-slate-300 px-3 py-2" value={values.instagram_username ?? ""} onChange={(event) => setValues({ ...values, instagram_username: event.target.value })} />
      </label>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
        Instagram profile URL
        <input className="min-h-11 rounded-md border border-slate-300 px-3 py-2" value={values.instagram_profile_url ?? ""} onChange={(event) => setValues({ ...values, instagram_profile_url: event.target.value })} />
      </label>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
        Source
        <select className="min-h-11 rounded-md border border-slate-300 px-3 py-2" value={values.lead_source_id ?? ""} onChange={(event) => setValues({ ...values, lead_source_id: event.target.value })}>
          <option value="">No source / Manual</option>
          {leadSources.map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}
        </select>
      </label>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
        Expected revenue
        <input className="min-h-11 rounded-md border border-slate-300 px-3 py-2" inputMode="decimal" min="0" step="0.01" type="number" value={values.expected_revenue ?? ""} onChange={(event) => setValues({ ...values, expected_revenue: event.target.value })} />
      </label>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
        Notes
        <textarea className="min-h-24 rounded-md border border-slate-300 px-3 py-2" value={values.notes ?? ""} onChange={(event) => setValues({ ...values, notes: event.target.value })} />
      </label>
      {validationError ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">{validationError}</p> : null}
      {submitError ? <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700">{submitError}</p> : null}
      <button className="min-h-11 rounded-md bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Creating…" : "Create lead"}
      </button>
    </form>
  );
}
