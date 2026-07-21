"use client";

import { FormEvent, useState } from "react";
import { useI18n } from "@/i18n/provider";
import { buildCustomerCreatePayload } from "@/lib/payload-builders";
import { CustomerCreatePayload } from "@/services/crm";
import { Button, FormField, Input } from "@/components/ui/primitives";

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
      <FormField label={t("tables.name")} error={validationError}>
        <Input required value={values.name} onChange={(event) => setValues({ ...values, name: event.target.value })} />
      </FormField>
      <FormField label={t("tables.phone")}>
        <Input inputMode="tel" value={values.phone ?? ""} onChange={(event) => setValues({ ...values, phone: event.target.value })} />
      </FormField>
      <FormField label={t("tables.instagram")}>
        <Input autoCapitalize="none" value={values.instagram_username ?? ""} onChange={(event) => setValues({ ...values, instagram_username: event.target.value })} />
      </FormField>
      <div className="grid min-w-0 gap-4 md:grid-cols-2">
        <FormField label={t("shipments.city")}>
          <Input value={values.city ?? ""} onChange={(event) => setValues({ ...values, city: event.target.value })} />
        </FormField>
        <FormField label={t("customers.region")}>
          <Input value={values.region ?? ""} onChange={(event) => setValues({ ...values, region: event.target.value })} />
        </FormField>
      </div>
      {submitError ? <p className="rounded-2xl border border-danger/25 bg-[var(--danger-surface)] px-3 py-2 text-sm font-bold text-[var(--danger-foreground)]">{submitError}</p> : null}
      <Button className="w-full" loading={isSubmitting} type="submit">{t("customers.create")}</Button>
    </form>
  );
}
