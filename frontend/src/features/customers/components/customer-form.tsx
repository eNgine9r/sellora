"use client";

import { FormEvent, useState } from "react";
import { useI18n } from "@/i18n/provider";
import { buildCustomerCreatePayload } from "@/lib/payload-builders";
import { CustomerCreatePayload } from "@/services/crm";

export type CustomerFormValues = {
  name: string;
  phone?: string;
  instagram_username?: string;
  city?: string;
  region?: string;
};

export function CustomerForm({ onSubmit, isSubmitting = false, submitError }: { onSubmit: (values: CustomerCreatePayload) => void; isSubmitting?: boolean; submitError?: string | null }) {
  const { t } = useI18n();
  const [values, setValues] = useState<CustomerFormValues>({ name: "" });
  const [validationError, setValidationError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = buildCustomerCreatePayload(values);
    if (!payload.name) {
      setValidationError(t("customers.nameRequired"));
      return;
    }
    setValidationError(null);
    onSubmit(payload);
  }

  return (
    <form className="grid min-w-0 gap-4 overflow-x-hidden" onSubmit={submit} noValidate>
      <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">
        {t("tables.name")}
        <input className="min-w-0 rounded-md border border-slate-300 px-3 py-2" required value={values.name} onChange={(event) => setValues({ ...values, name: event.target.value })} />
      </label>
      <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">
        {t("tables.phone")}
        <input className="min-w-0 rounded-md border border-slate-300 px-3 py-2" value={values.phone ?? ""} onChange={(event) => setValues({ ...values, phone: event.target.value })} />
      </label>
      <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">
        {t("tables.instagram")}
        <input className="min-w-0 rounded-md border border-slate-300 px-3 py-2" value={values.instagram_username ?? ""} onChange={(event) => setValues({ ...values, instagram_username: event.target.value })} />
      </label>
      <div className="grid min-w-0 gap-4 md:grid-cols-2">
        <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">
          {t("shipments.city")}
          <input className="min-w-0 rounded-md border border-slate-300 px-3 py-2" value={values.city ?? ""} onChange={(event) => setValues({ ...values, city: event.target.value })} />
        </label>
        <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">
          {t("customers.region")}
          <input className="min-w-0 rounded-md border border-slate-300 px-3 py-2" value={values.region ?? ""} onChange={(event) => setValues({ ...values, region: event.target.value })} />
        </label>
      </div>
      {validationError ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">{validationError}</p> : null}
      {submitError ? <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700">{submitError}</p> : null}
      <button className="min-h-11 w-full rounded-md bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60" disabled={isSubmitting} type="submit">{isSubmitting ? t("customers.creating") : t("customers.create")}</button>
    </form>
  );
}
