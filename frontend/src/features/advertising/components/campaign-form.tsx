"use client";

import { FormEvent, useState } from "react";
import { buildAdCampaignCreatePayload } from "@/lib/payload-builders";
import { AdCampaignCreate } from "@/types/advertising";
import { useI18n } from "@/i18n/provider";
import { Button, FormField, Input, Select, Textarea } from "@/components/ui/primitives";

const PLATFORMS = [
  ["META", "Meta"], ["INSTAGRAM", "Instagram"], ["FACEBOOK", "Facebook"], ["TIKTOK", "TikTok"], ["GOOGLE", "Google"], ["TELEGRAM", "Telegram"], ["OTHER", "Інше"],
] as const;
const STATUSES = [["ACTIVE", "Активна"], ["PAUSED", "Призупинена"], ["COMPLETED", "Завершена"], ["ARCHIVED", "Архівна"]] as const;
const OBJECTIVES = [["MESSAGES", "Повідомлення"], ["SALES", "Продажі"], ["TRAFFIC", "Трафік"], ["AWARENESS", "Впізнаваність"], ["FOLLOWERS", "Підписники"], ["OTHER", "Інше"]] as const;
const BUDGET_TYPES = [["DAILY", "Денний"], ["LIFETIME", "На весь період"], ["MANUAL", "Ручний"]] as const;

export function CampaignForm({ onSubmit }: { onSubmit?: (payload: AdCampaignCreate) => void }) {
  const { t } = useI18n();
  const [values, setValues] = useState<Record<string, string>>({ name: "", platform: "INSTAGRAM", status: "ACTIVE", objective: "MESSAGES", budget_type: "MANUAL" });
  const [validationError, setValidationError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = buildAdCampaignCreatePayload(values);
    if (!payload.name) {
      setValidationError(t("errors.required"));
      return;
    }
    setValidationError(null);
    onSubmit?.(payload);
  }

  return (
    <form className="grid w-full min-w-0 max-w-full gap-4 overflow-x-hidden" onSubmit={submit} noValidate>
      <FormField label={t("advertising.campaignName")} error={validationError}>
        <Input required value={values.name ?? ""} onChange={(event) => setValues({ ...values, name: event.target.value })} />
      </FormField>
      <div className="grid min-w-0 gap-4 sm:grid-cols-2">
        <FormField label={t("advertising.platform")}>
          <Select value={values.platform} onChange={(event) => setValues({ ...values, platform: event.target.value })}>{PLATFORMS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Select>
        </FormField>
        <FormField label={t("tables.status")}>
          <Select value={values.status} onChange={(event) => setValues({ ...values, status: event.target.value })}>{STATUSES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Select>
        </FormField>
        <FormField label={t("advertising.objective")}>
          <Select value={values.objective} onChange={(event) => setValues({ ...values, objective: event.target.value })}>{OBJECTIVES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Select>
        </FormField>
        <FormField label="Тип бюджету">
          <Select value={values.budget_type} onChange={(event) => setValues({ ...values, budget_type: event.target.value })}>{BUDGET_TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Select>
        </FormField>
      </div>
      <div className="grid min-w-0 gap-4 sm:grid-cols-2">
        <FormField label={t("advertising.dailyBudget")}><Input inputMode="decimal" min="0" step="0.01" type="number" value={values.daily_budget ?? ""} onChange={(event) => setValues({ ...values, daily_budget: event.target.value })} /></FormField>
        <FormField label={t("advertising.totalBudget")}><Input inputMode="decimal" min="0" step="0.01" type="number" value={values.total_budget ?? ""} onChange={(event) => setValues({ ...values, total_budget: event.target.value })} /></FormField>
        <FormField label="Дата початку"><Input className="sellora-date-input" type="date" value={values.start_date ?? ""} onChange={(event) => setValues({ ...values, start_date: event.target.value })} /></FormField>
        <FormField label="Дата завершення"><Input className="sellora-date-input" type="date" value={values.end_date ?? ""} onChange={(event) => setValues({ ...values, end_date: event.target.value })} /></FormField>
      </div>
      <FormField label={t("advertising.notes")}><Textarea value={values.notes ?? ""} onChange={(event) => setValues({ ...values, notes: event.target.value })} /></FormField>
      <Button className="w-full" type="submit">{t("advertising.createCampaign")}</Button>
    </form>
  );
}
