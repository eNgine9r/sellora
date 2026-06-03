"use client";

import { FormEvent, useState } from "react";
import { LeadSource } from "@/types/crm";

export type LeadFormValues = {
  name: string;
  phone?: string;
  instagram_username?: string;
  instagram_profile_url?: string;
  lead_source_id?: string;
  notes?: string;
};

export function LeadForm({ leadSources, onSubmit }: { leadSources: LeadSource[]; onSubmit: (values: LeadFormValues) => void }) {
  const [values, setValues] = useState<LeadFormValues>({ name: "" });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit(values);
    setValues({ name: "" });
  }

  return (
    <form className="grid gap-4" onSubmit={submit}>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
        Name
        <input className="rounded-md border border-slate-300 px-3 py-2" required value={values.name} onChange={(event) => setValues({ ...values, name: event.target.value })} />
      </label>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
        Phone
        <input className="rounded-md border border-slate-300 px-3 py-2" value={values.phone ?? ""} onChange={(event) => setValues({ ...values, phone: event.target.value })} />
      </label>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
        Instagram username
        <input className="rounded-md border border-slate-300 px-3 py-2" value={values.instagram_username ?? ""} onChange={(event) => setValues({ ...values, instagram_username: event.target.value })} />
      </label>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
        Instagram profile URL
        <input className="rounded-md border border-slate-300 px-3 py-2" value={values.instagram_profile_url ?? ""} onChange={(event) => setValues({ ...values, instagram_profile_url: event.target.value })} />
      </label>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
        Source
        <select className="rounded-md border border-slate-300 px-3 py-2" value={values.lead_source_id ?? ""} onChange={(event) => setValues({ ...values, lead_source_id: event.target.value || undefined })}>
          <option value="">Manual</option>
          {leadSources.map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}
        </select>
      </label>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
        Notes
        <textarea className="rounded-md border border-slate-300 px-3 py-2" value={values.notes ?? ""} onChange={(event) => setValues({ ...values, notes: event.target.value })} />
      </label>
      <button className="rounded-md bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700" type="submit">Create lead</button>
    </form>
  );
}
