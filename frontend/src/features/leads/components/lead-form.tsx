"use client";

import { FormEvent, useState } from "react";
import { useI18n } from "@/i18n/provider";
import { buildLeadCreatePayload } from "@/lib/payload-builders";
import { LeadCreatePayload } from "@/services/crm";
import { LeadSource } from "@/types/crm";
import { AdCampaign } from "@/types/advertising";
import { Button, FormField, Input, Select, Textarea } from "@/components/ui/primitives";

export type LeadFormValues = {
  name: string;
  phone?: string;
  instagram_username?: string;
  instagram_profile_url?: string;
  lead_source_id?: string;
  campaign_id?: string;
  notes?: string;
  assigned_user_id?: string;
  expected_revenue?: string;
};

export function LeadForm({ leadSources, campaigns = [], onSubmit, isSubmitting = false, submitError }: { leadSources: LeadSource[]; campaigns?: AdCampaign[]; onSubmit: (payload: LeadCreatePayload) => Promise<void> | void; isSubmitting?: boolean; submitError?: string | null }) {
  const { t } = useI18n();
  const [values, setValues] = useState<LeadFormValues>({ name: "" });
  const [validationError, setValidationError] = useState<string | null>(null);
  const expectedRevenueLabel = t("advertising.revenue") === "Revenue" ? "Expected revenue" : "Очікуваний дохід";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = buildLeadCreatePayload(values);
    if (!payload.name) {
      setValidationError(t("errors.required"));
      return;
    }
    setValidationError(null);
    await onSubmit(payload);
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
      <FormField label="URL профілю Instagram">
        <Input inputMode="url" type="url" value={values.instagram_profile_url ?? ""} onChange={(event) => setValues({ ...values, instagram_profile_url: event.target.value })} />
      </FormField>
      <FormField label={t("leads.source")}>
        <Select value={values.lead_source_id ?? ""} onChange={(event) => setValues({ ...values, lead_source_id: event.target.value })}>
          <option value="">{t("leads.noSource")}</option>
          {leadSources.map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}
        </Select>
      </FormField>
      <FormField label={t("leads.campaignLabel")} hint={t("leads.campaignHelp")}>
        <Select value={values.campaign_id ?? ""} onChange={(event) => setValues({ ...values, campaign_id: event.target.value })}>
          <option value="">{t("leads.noCampaign")}</option>
          {campaigns.map((campaign) => <option key={campaign.id} value={campaign.id}>{campaign.name} · {campaign.platform}</option>)}
        </Select>
      </FormField>
      <FormField label={expectedRevenueLabel}>
        <Input inputMode="decimal" min="0" step="0.01" type="number" value={values.expected_revenue ?? ""} onChange={(event) => setValues({ ...values, expected_revenue: event.target.value })} />
      </FormField>
      <FormField label={t("orders.notes")}>
        <Textarea value={values.notes ?? ""} onChange={(event) => setValues({ ...values, notes: event.target.value })} />
      </FormField>
      {submitError ? <p className="rounded-2xl border border-danger/25 bg-[var(--danger-surface)] px-3 py-2 text-sm font-bold text-[var(--danger-foreground)]">{submitError}</p> : null}
      <Button className="w-full" loading={isSubmitting} type="submit">{t("leads.create")}</Button>
    </form>
  );
}
