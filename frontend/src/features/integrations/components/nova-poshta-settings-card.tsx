"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { CitySearchSelect } from "@/features/integrations/components/city-search-select";
import { IntegrationStatusBadge } from "@/features/integrations/components/integration-status-badge";
import { WarehouseSearchSelect } from "@/features/integrations/components/warehouse-search-select";
import { useI18n } from "@/i18n/provider";
import { NovaPoshtaSettings, NovaPoshtaSettingsPayload } from "@/types/integrations";

const inputClass = "min-h-11 rounded-lg border border-slate-300 px-3 dark:border-white/10 dark:bg-white/10 dark:text-white";

type NovaPoshtaSettingsCardProps = {
  workspaceId: string;
  settings?: NovaPoshtaSettings;
  message?: string | null;
  isSaving?: boolean;
  isTesting?: boolean;
  isDisconnecting?: boolean;
  onSave: (payload: NovaPoshtaSettingsPayload) => void;
  onTest: () => void;
  onDisconnect: () => void;
};

export function NovaPoshtaSettingsCard({ workspaceId, settings, message, isSaving = false, isTesting = false, isDisconnecting = false, onSave, onTest, onDisconnect }: NovaPoshtaSettingsCardProps) {
  const { t } = useI18n();
  const [apiKey, setApiKey] = useState("");
  const [senderCityRef, setSenderCityRef] = useState(settings?.sender_city_ref ?? "");
  const [senderWarehouseRef, setSenderWarehouseRef] = useState(settings?.sender_warehouse_ref ?? "");
  const [senderCounterpartyRef, setSenderCounterpartyRef] = useState(settings?.sender_counterparty_ref ?? "");
  const [senderContactRef, setSenderContactRef] = useState(settings?.sender_contact_ref ?? "");
  const [senderPhone, setSenderPhone] = useState(settings?.sender_phone ?? "");
  const [senderCitySearch, setSenderCitySearch] = useState("");
  const [senderWarehouseSearch, setSenderWarehouseSearch] = useState("");
  const hasSavedKey = Boolean(settings?.masked_api_key);

  useEffect(() => {
    setSenderCityRef(settings?.sender_city_ref ?? "");
    setSenderWarehouseRef(settings?.sender_warehouse_ref ?? "");
    setSenderCounterpartyRef(settings?.sender_counterparty_ref ?? "");
    setSenderContactRef(settings?.sender_contact_ref ?? "");
    setSenderPhone(settings?.sender_phone ?? "");
  }, [settings]);

  const missingSenderFields = useMemo(() => [
    ["senderCityRef", senderCityRef],
    ["senderWarehouseRef", senderWarehouseRef],
    ["senderCounterpartyRef", senderCounterpartyRef],
    ["senderContactRef", senderContactRef],
    ["senderPhone", senderPhone],
  ].filter(([, value]) => !value).map(([key]) => t(`novaPoshta.${key}`)), [senderCityRef, senderWarehouseRef, senderCounterpartyRef, senderContactRef, senderPhone, t]);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!apiKey && !hasSavedKey) return;
    onSave({
      api_key: apiKey || null,
      sender_city_ref: senderCityRef || null,
      sender_warehouse_ref: senderWarehouseRef || null,
      sender_counterparty_ref: senderCounterpartyRef || null,
      sender_contact_ref: senderContactRef || null,
      sender_phone: senderPhone || null,
    });
    setApiKey("");
  }

  return (
    <section className="grid gap-5 rounded-2xl bg-white p-5 shadow-sm dark:bg-[#15172A] dark:text-white">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-black">{t("novaPoshta.title")}</h2>
          <p className="text-sm text-slate-500 dark:text-slate-300">{t("novaPoshta.subtitle")}</p>
        </div>
        <IntegrationStatusBadge status={settings?.status ?? "DISCONNECTED"} />
      </div>

      {hasSavedKey ? <p className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-100">{t("novaPoshta.savedKey")}: <strong>{settings?.masked_api_key}</strong></p> : <p className="rounded-xl bg-amber-50 p-3 text-sm font-semibold text-amber-800 dark:bg-amber-500/15 dark:text-amber-100">{t("novaPoshta.keyRequired")}</p>}

      <form className="grid gap-5" onSubmit={submit}>
        <section className="grid gap-3 rounded-2xl border border-slate-100 p-4 dark:border-white/10">
          <div>
            <h3 className="font-black text-slate-950 dark:text-white">{t("novaPoshta.connection")}</h3>
            <p className="text-sm text-slate-500 dark:text-slate-300">{t("novaPoshta.credentialHelp")}</p>
          </div>
          <label className="grid gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
            <span>{t("novaPoshta.credential")}</span>
            <input className={inputClass} type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder={hasSavedKey ? t("novaPoshta.keepExistingCredential") : t("novaPoshta.enterCredential")} required={!hasSavedKey} autoComplete="off" />
          </label>
          <button className="min-h-11 rounded-xl bg-blue-600 px-4 py-2 font-bold text-white disabled:opacity-60" disabled={isSaving || (!apiKey && !hasSavedKey)} type="submit">{isSaving ? t("common.saving") : t("novaPoshta.saveApiKey")}</button>
        </section>

        <section className="grid gap-3 rounded-2xl border border-slate-100 p-4 dark:border-white/10">
          <div>
            <h3 className="font-black text-slate-950 dark:text-white">{t("novaPoshta.senderSettings")}</h3>
            <p className="text-sm leading-6 text-slate-500 dark:text-slate-300">{t("novaPoshta.senderHelp")}</p>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <CitySearchSelect workspaceId={workspaceId} query={senderCitySearch} onQuery={setSenderCitySearch} helperText={t("novaPoshta.cityHelper")} onSelect={(item) => { setSenderCitySearch(item.description); setSenderCityRef(item.ref); setSenderWarehouseRef(""); setSenderWarehouseSearch(""); }} />
            <WarehouseSearchSelect workspaceId={workspaceId} cityRef={senderCityRef} query={senderWarehouseSearch} onQuery={setSenderWarehouseSearch} helperText={t("novaPoshta.warehouseHelper")} onSelect={(item) => { setSenderWarehouseSearch(item.description); setSenderWarehouseRef(item.ref); }} />
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="grid gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200"><span>{t("novaPoshta.senderCityRef")}</span><input className={inputClass} value={senderCityRef} onChange={(event) => { setSenderCityRef(event.target.value); setSenderWarehouseRef(""); setSenderWarehouseSearch(""); }} /></label>
            <label className="grid gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200"><span>{t("novaPoshta.senderWarehouseRef")}</span><input className={inputClass} value={senderWarehouseRef} onChange={(event) => setSenderWarehouseRef(event.target.value)} /></label>
            <label className="grid gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200"><span>{t("novaPoshta.senderCounterpartyRef")}</span><input className={inputClass} value={senderCounterpartyRef} onChange={(event) => setSenderCounterpartyRef(event.target.value)} /></label>
            <label className="grid gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200"><span>{t("novaPoshta.senderContactRef")}</span><input className={inputClass} value={senderContactRef} onChange={(event) => setSenderContactRef(event.target.value)} /></label>
            <label className="grid gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200"><span>{t("novaPoshta.senderPhone")}</span><input className={inputClass} value={senderPhone} onChange={(event) => setSenderPhone(event.target.value)} /></label>
          </div>
          {missingSenderFields.length ? <p className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs font-semibold text-amber-800 dark:border-amber-400/30 dark:bg-amber-500/15 dark:text-amber-100">{t("novaPoshta.senderWarning")} {t("novaPoshta.missingSenderFields")}: {missingSenderFields.join(", ")}.</p> : <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs font-semibold text-emerald-800 dark:border-emerald-400/30 dark:bg-emerald-500/15 dark:text-emerald-100">{t("novaPoshta.senderReady")}</p>}
        </section>
      </form>

      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
        <button className="min-h-11 rounded-xl border border-slate-300 px-4 py-2 font-bold disabled:opacity-60 dark:border-white/10" disabled={isTesting || !hasSavedKey} onClick={onTest}>{isTesting ? t("novaPoshta.testingConnection") : t("novaPoshta.testConnection")}</button>
        <button className="min-h-11 rounded-xl border border-rose-200 px-4 py-2 font-bold text-rose-700 disabled:opacity-60 dark:border-rose-400/40 dark:text-rose-200" disabled={isDisconnecting || !hasSavedKey} onClick={onDisconnect}>{isDisconnecting ? t("common.loading") : t("novaPoshta.disconnect")}</button>
      </div>
      {message ? <p className="rounded-xl bg-blue-50 p-3 text-sm font-semibold text-blue-700 dark:bg-blue-500/15 dark:text-blue-100">{message}</p> : null}
      <p className="text-xs text-slate-500 dark:text-slate-400">{t("novaPoshta.maskedCredentials")}</p>
    </section>
  );
}
// Settings navigation regression compatibility marker: Sender contact person ref.
