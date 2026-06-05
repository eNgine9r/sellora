"use client";

import { FormEvent, useState } from "react";
import { useI18n } from "@/i18n/provider";
import { buildProductCreatePayload } from "@/lib/payload-builders";
import { translatedCategoryOptions } from "@/lib/categories";
import { ProductCreatePayload } from "@/services/products";

export type ProductFormValues = {
  name: string;
  sku?: string;
  category?: string;
  brand?: string;
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
  const { t } = useI18n();
  const categoryOptions = translatedCategoryOptions(t);
  const [values, setValues] = useState<ProductFormValues>({ name: "", category: "other" });
  const [validationError, setValidationError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = buildProductCreatePayload(values);
    if (!payload.name) {
      setValidationError(t("errors.required"));
      return;
    }
    setValidationError(null);
    onSubmit(payload);
  }

  return (
    <form className="grid min-w-0 gap-4 overflow-x-hidden" onSubmit={submit} noValidate>
      <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">
        {t("tables.name")}
        <input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" required value={values.name} onChange={(event) => setValues({ ...values, name: event.target.value })} />
      </label>
      <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">
        SKU
        <input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" value={values.sku ?? ""} onChange={(event) => setValues({ ...values, sku: event.target.value })} />
      </label>
      <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">
        {t("products.productCategory")}
        <select className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" value={values.category ?? "other"} onChange={(event) => setValues({ ...values, category: event.target.value })}>
          {categoryOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
      </label>
      <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">
        {t("products.brand")}
        <input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" value={values.brand ?? ""} onChange={(event) => setValues({ ...values, brand: event.target.value })} />
      </label>
      <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">
        {t("products.primaryImageUrl")}
        <input className="min-h-11 min-w-0 rounded-md border border-slate-300 px-3 py-2" value={values.image_url ?? ""} onChange={(event) => setValues({ ...values, image_url: event.target.value })} />
      </label>
      <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700 dark:text-slate-200">
        {t("products.description")}
        <textarea className="min-w-0 rounded-md border border-slate-300 px-3 py-2" value={values.description ?? ""} onChange={(event) => setValues({ ...values, description: event.target.value })} />
      </label>
      {validationError ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700 dark:bg-amber-500/15 dark:text-amber-100">{validationError}</p> : null}
      {submitError ? <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700 dark:bg-rose-500/15 dark:text-rose-100">{submitError}</p> : null}
      <button className="min-h-11 w-full rounded-md bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60" disabled={isSubmitting} type="submit">
        {isSubmitting ? t("common.loading") : t("products.create")}
      </button>
    </form>
  );
}
