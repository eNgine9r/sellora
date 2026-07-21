"use client";

import { FormEvent, useState } from "react";
import { useI18n } from "@/i18n/provider";
import { buildProductCreatePayload } from "@/lib/payload-builders";
import { translatedCategoryOptions } from "@/lib/categories";
import { ProductCreatePayload } from "@/services/products";
import { Button, FormField, Input, Select, Textarea } from "@/components/ui/primitives";

export type ProductFormValues = {
  name: string;
  sku?: string;
  category?: string;
  brand?: string;
  description?: string;
  image_url?: string;
};

export function ProductForm({ onSubmit, isSubmitting = false, submitError }: { onSubmit: (values: ProductCreatePayload) => void; isSubmitting?: boolean; submitError?: string | null }) {
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
      <FormField label={t("tables.name")} error={validationError}>
        <Input required value={values.name} onChange={(event) => setValues({ ...values, name: event.target.value })} />
      </FormField>
      <FormField label="SKU">
        <Input value={values.sku ?? ""} onChange={(event) => setValues({ ...values, sku: event.target.value })} />
      </FormField>
      <FormField label={t("products.productCategory")}>
        <Select value={values.category ?? "other"} onChange={(event) => setValues({ ...values, category: event.target.value })}>
          {categoryOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </Select>
      </FormField>
      <FormField label={t("products.brand")}>
        <Input value={values.brand ?? ""} onChange={(event) => setValues({ ...values, brand: event.target.value })} />
      </FormField>
      <FormField label={t("products.primaryImageUrl")}>
        <Input inputMode="url" type="url" value={values.image_url ?? ""} onChange={(event) => setValues({ ...values, image_url: event.target.value })} />
      </FormField>
      <FormField label={t("products.description")}>
        <Textarea value={values.description ?? ""} onChange={(event) => setValues({ ...values, description: event.target.value })} />
      </FormField>
      {submitError ? <p className="rounded-2xl border border-danger/25 bg-[var(--danger-surface)] px-3 py-2 text-sm font-bold text-[var(--danger-foreground)]">{submitError}</p> : null}
      <Button className="w-full" loading={isSubmitting} type="submit">{t("products.create")}</Button>
    </form>
  );
}
