"use client";

import { FormEvent, useState } from "react";
import { buildProductCreatePayload } from "@/lib/payload-builders";
import { ProductCreatePayload } from "@/services/products";

export type ProductFormValues = {
  name: string;
  sku?: string;
  description?: string;
  image_url?: string;
};

export function ProductForm({
  onSubmit,
  isSubmitting = false,
  submitError,
}: {
  onSubmit: (values: ProductCreatePayload) => void;
  isSubmitting?: boolean;
  submitError?: string | null;
}) {
  const [values, setValues] = useState<ProductFormValues>({ name: "" });
  const [validationError, setValidationError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = buildProductCreatePayload(values);
    if (!payload.name) {
      setValidationError("Product name is required.");
      return;
    }
    setValidationError(null);
    onSubmit(payload);
  }

  return (
    <form className="grid min-w-0 gap-4 overflow-x-hidden" onSubmit={submit} noValidate>
      <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">
        Name
        <input className="min-w-0 rounded-md border border-slate-300 px-3 py-2" required value={values.name} onChange={(event) => setValues({ ...values, name: event.target.value })} />
      </label>
      <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">
        SKU
        <input className="min-w-0 rounded-md border border-slate-300 px-3 py-2" value={values.sku ?? ""} onChange={(event) => setValues({ ...values, sku: event.target.value })} />
      </label>
      <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">
        Primary image URL
        <input className="min-w-0 rounded-md border border-slate-300 px-3 py-2" value={values.image_url ?? ""} onChange={(event) => setValues({ ...values, image_url: event.target.value })} />
      </label>
      <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">
        Description
        <textarea className="min-w-0 rounded-md border border-slate-300 px-3 py-2" value={values.description ?? ""} onChange={(event) => setValues({ ...values, description: event.target.value })} />
      </label>
      {validationError ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">{validationError}</p> : null}
      {submitError ? <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700">{submitError}</p> : null}
      <button className="min-h-11 w-full rounded-md bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Creating…" : "Create product"}
      </button>
    </form>
  );
}
