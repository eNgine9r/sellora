"use client";

import { FormEvent, useState } from "react";
import { buildCustomerCreatePayload } from "@/lib/payload-builders";
import { CustomerCreatePayload } from "@/services/crm";

export type CustomerFormValues = {
  name: string;
  phone?: string;
  instagram_username?: string;
  city?: string;
  region?: string;
};

export function CustomerForm({ onSubmit }: { onSubmit: (values: CustomerCreatePayload) => void }) {
  const [values, setValues] = useState<CustomerFormValues>({ name: "" });
  const [validationError, setValidationError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = buildCustomerCreatePayload(values);
    if (!payload.name) {
      setValidationError("Customer name is required.");
      return;
    }
    setValidationError(null);
    onSubmit(payload);
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
      <div className="grid gap-4 md:grid-cols-2">
        <label className="grid gap-1 text-sm font-medium text-slate-700">
          City
          <input className="rounded-md border border-slate-300 px-3 py-2" value={values.city ?? ""} onChange={(event) => setValues({ ...values, city: event.target.value })} />
        </label>
        <label className="grid gap-1 text-sm font-medium text-slate-700">
          Region
          <input className="rounded-md border border-slate-300 px-3 py-2" value={values.region ?? ""} onChange={(event) => setValues({ ...values, region: event.target.value })} />
        </label>
      </div>
      {validationError ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">{validationError}</p> : null}
      <button className="rounded-md bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700" type="submit">Create customer</button>
    </form>
  );
}
