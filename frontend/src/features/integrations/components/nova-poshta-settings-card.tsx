"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { searchNovaPoshtaSenders, fetchNovaPoshtaSenderContacts } from "@/services/integrations";
import type { FormEvent } from "react";
import { CitySearchSelect } from "@/features/integrations/components/city-search-select";
import { IntegrationStatusBadge } from "@/features/integrations/components/integration-status-badge";
import { WarehouseSearchSelect } from "@/features/integrations/components/warehouse-search-select";
import { useI18n } from "@/i18n/provider";
import { NovaPoshtaSettings, NovaPoshtaSettingsPayload } from "@/types/integrations";

const inputClass = "w-full min-w-0 min-h-11 rounded-lg border border-slate-300 px-3 dark:border-white/10 dark:bg-white/10 dark:text-white";

type NovaPoshtaSettingsCardProps = {
  workspaceId: string;
  settings?: NovaPoshtaSettings;
  message?: string | null;
  isSaving?: boolean;
  isTesting?: boolean;
  isUpdatingPermission?: boolean;
  isDisconnecting?: boolean;
  onSave: (payload: NovaPoshtaSettingsPayload) => void;
  onTest: () => void;
  onUpdateWritePermission: (allowed: boolean) => void;
  onDisconnect: () => void;
};

export function NovaPoshtaSettingsCard({ workspaceId, settings, message, isSaving = false, isTesting = false, isUpdatingPermission = false, isDisconnecting = false, onSave, onTest, onUpdateWritePermission, onDisconnect }: NovaPoshtaSettingsCardProps) {
  const { t } = useI18n();
  const [apiKey, setApiKey] = useState("");
  const [senderCityRef, setSenderCityRef] = useState(settings?.sender_city_ref ?? "");
  const [senderWarehouseRef, setSenderWarehouseRef] = useState(settings?.sender_warehouse_ref ?? "");
  const [senderCounterpartyRef, setSenderCounterpartyRef] = useState(settings?.sender_counterparty_ref ?? "");
  const [senderContactRef, setSenderContactRef] = useState(settings?.sender_contact_ref ?? "");
  const [senderPhone, setSenderPhone] = useState(settings?.sender_phone ?? "");
  const [senderCitySearch, setSenderCitySearch] = useState("");
  const [senderWarehouseSearch, setSenderWarehouseSearch] = useState("");
  const [senderQuery, setSenderQuery] = useState("");
  const [senderPage, setSenderPage] = useState(1);
  const senders = useQuery({ queryKey: ["np-senders", workspaceId, senderQuery, senderPage, settings?.masked_api_key], queryFn: () => searchNovaPoshtaSenders(workspaceId, senderQuery, senderPage), enabled: Boolean(settings?.masked_api_key), retry: false });
  const contacts = useQuery({ queryKey: ["np-sender-contacts", workspaceId, senderCounterpartyRef, settings?.masked_api_key], queryFn: () => fetchNovaPoshtaSenderContacts(workspaceId, senderCounterpartyRef), enabled: Boolean(settings?.masked_api_key && senderCounterpartyRef), retry: false });
  const hasSavedKey = Boolean(settings?.masked_api_key);
  const connectionReady = settings?.status === "CONNECTED" && hasSavedKey;
  const activationPrerequisitesReady = Boolean(
    settings?.environment_capability
    && connectionReady
    && settings.sender_configured
    && settings.connection_verified,
  );
  const activationItems = [
    { label: t("novaPoshta.activationEnvironment"), ready: Boolean(settings?.environment_capability) },
    { label: t("novaPoshta.activationConnection"), ready: connectionReady },
    { label: t("novaPoshta.activationSender"), ready: Boolean(settings?.sender_configured) },
    { label: t("novaPoshta.activationVerification"), ready: Boolean(settings?.connection_verified) },
    { label: t("novaPoshta.activationPermission"), ready: Boolean(settings?.workspace_permission) },
  ];

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
      api_key: apiKey.trim() || null,
      sender_city_ref: senderCityRef || null,
      sender_warehouse_ref: senderWarehouseRef || null,
      sender_counterparty_ref: senderCounterpartyRef || null,
      sender_contact_ref: senderContactRef || null,
      sender_phone: senderPhone || null,
    });
    setApiKey("");
  }

  return (
    <section data-nova-poshta-settings className="grid min-w-0 gap-5 rounded-2xl bg-white p-5 shadow-sm dark:bg-[#15172A] dark:text-white">
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
            <p className="text-sm text-slate-500 dark:text-slate-300">{t("novaPoshta.onboardingHelp")}</p>
            <a className="text-sm font-bold text-blue-600 underline" href="https://new.novaposhta.ua/dashboard/settings/developers" target="_blank" rel="noopener noreferrer">{t("novaPoshta.openSecurity")}</a>
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
          <div className="grid min-w-0 gap-3 sm:grid-cols-2 [&>*]:min-w-0">
            <CitySearchSelect workspaceId={workspaceId} query={senderCitySearch} onQuery={(value) => { setSenderCitySearch(value); setSenderCityRef(""); setSenderWarehouseRef(""); setSenderWarehouseSearch(""); }} helperText={t("novaPoshta.cityHelper")} onSelect={(item) => { setSenderCitySearch(item.description); setSenderCityRef(item.ref); setSenderWarehouseRef(""); setSenderWarehouseSearch(""); }} />
            <WarehouseSearchSelect workspaceId={workspaceId} cityRef={senderCityRef} query={senderWarehouseSearch} onQuery={(value) => { setSenderWarehouseSearch(value); setSenderWarehouseRef(""); }} helperText={t("novaPoshta.warehouseHelper")} onSelect={(item) => { setSenderWarehouseSearch(item.description); setSenderWarehouseRef(item.ref); }} />
          </div>
          <div className="grid min-w-0 gap-3 sm:grid-cols-2 [&>*]:min-w-0">
            <label className="grid gap-2 text-sm font-semibold"><span>{t("novaPoshta.senderSearch")}</span><input className={inputClass} value={senderQuery} maxLength={100} onChange={(event) => { setSenderQuery(event.target.value); setSenderPage(1); }} disabled={!hasSavedKey} /></label>
            <label className="grid gap-2 text-sm font-semibold"><span>{t("novaPoshta.senderName")}</span><select aria-label={t("novaPoshta.senderName")} className={inputClass} value={senderCounterpartyRef} disabled={!hasSavedKey || senders.isFetching} onChange={(event) => { setSenderCounterpartyRef(event.target.value); setSenderContactRef(""); setSenderCityRef(""); setSenderWarehouseRef(""); setSenderCitySearch(""); setSenderWarehouseSearch(""); }}><option value="">{t("novaPoshta.chooseSender")}</option>{senderCounterpartyRef && !senders.data?.some(item => item.ref === senderCounterpartyRef) ? <option value={senderCounterpartyRef}>{t("novaPoshta.savedSender")}</option> : null}{senders.data?.map(item => <option key={item.ref} value={item.ref}>{item.description}</option>)}</select></label>
            <div className="flex min-w-0 flex-wrap gap-2"><button type="button" className="min-h-11 rounded-lg border px-3 disabled:opacity-50" disabled={senderPage === 1 || senders.isFetching} onClick={() => setSenderPage(page => page - 1)}>{t("novaPoshta.previousSenders")}</button><button type="button" className="min-h-11 rounded-lg border px-3 disabled:opacity-50" disabled={!senders.data?.length || senders.data.length < 20 || senders.isFetching || senderPage >= 100} onClick={() => setSenderPage(page => page + 1)}>{t("novaPoshta.nextSenders")}</button></div>
            <label className="grid gap-2 text-sm font-semibold"><span>{t("novaPoshta.contactName")}</span><select aria-label={t("novaPoshta.contactName")} className={inputClass} value={senderContactRef} disabled={!senderCounterpartyRef || contacts.isFetching} onChange={(event) => setSenderContactRef(event.target.value)}><option value="">{t("novaPoshta.chooseContact")}</option>{senderContactRef && !contacts.data?.some(item => item.ref === senderContactRef) ? <option value={senderContactRef}>{t("novaPoshta.savedContact")}</option> : null}{contacts.data?.map(item => <option key={item.ref} value={item.ref}>{item.description}</option>)}</select></label>
            <label className="grid gap-2 text-sm font-semibold"><span>{t("novaPoshta.senderPhone")}</span><input type="tel" className={inputClass} value={senderPhone} onChange={(event) => setSenderPhone(event.target.value)} /></label>
          </div>
          {senders.isFetching || contacts.isFetching ? <p role="status" className="text-sm">{t("common.loading")}</p> : null}
          {senders.isError || contacts.isError ? <p role="alert" className="text-sm text-amber-700">{t("novaPoshta.senderLookupFailed")} <button type="button" className="underline" onClick={() => { void senders.refetch(); if (senderCounterpartyRef) void contacts.refetch(); }}>{t("novaPoshta.retryLookup")}</button></p> : null}
          {senders.isSuccess && !senders.data.length ? <p className="text-sm">{t("novaPoshta.noSenders")}</p> : null}
          {contacts.isSuccess && !contacts.data.length ? <p className="text-sm">{t("novaPoshta.noContacts")}</p> : null}
          <button type="submit" className="min-h-11 rounded-xl bg-blue-600 px-4 py-2 font-bold text-white disabled:opacity-60" disabled={isSaving || !hasSavedKey || missingSenderFields.length > 0}>{t("novaPoshta.saveSender")}</button>
          {missingSenderFields.length ? <p className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs font-semibold text-amber-800 dark:border-amber-400/30 dark:bg-amber-500/15 dark:text-amber-100">{t("novaPoshta.senderWarning")} {t("novaPoshta.missingSenderFields")}: {missingSenderFields.join(", ")}.</p> : <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs font-semibold text-emerald-800 dark:border-emerald-400/30 dark:bg-emerald-500/15 dark:text-emerald-100">{t("novaPoshta.senderReady")}</p>}
        </section>
      </form>

      <p role="status" className="rounded-xl bg-blue-50 p-3 text-sm text-blue-800 dark:bg-blue-500/15 dark:text-blue-100">{t(!hasSavedKey ? "novaPoshta.nextKey" : !settings?.sender_configured ? "novaPoshta.nextSender" : !settings?.connection_verified ? "novaPoshta.nextVerify" : !settings?.workspace_permission ? "novaPoshta.nextPermission" : "novaPoshta.nextReady")}</p>
      <section className="grid gap-4 rounded-2xl border border-slate-200 p-4 dark:border-white/10" aria-labelledby="nova-poshta-activation-title">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h3 className="font-black text-slate-950 dark:text-white" id="nova-poshta-activation-title">{t("novaPoshta.activationTitle")}</h3>
            <p className="text-sm leading-6 text-slate-500 dark:text-slate-300">{t("novaPoshta.activationDescription")}</p>
          </div>
          <span className={`w-fit rounded-full px-3 py-1 text-xs font-black ${settings?.provider_writes_enabled ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-100" : "bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-amber-100"}`}>
            {t(settings?.provider_writes_enabled ? "novaPoshta.activationReady" : "novaPoshta.activationNeedsAction")}
          </span>
        </div>
        <ul className="grid gap-2 sm:grid-cols-2">
          {activationItems.map((item) => (
            <li className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200" key={item.label}>
              <span aria-hidden="true" className={`h-2.5 w-2.5 shrink-0 rounded-full ${item.ready ? "bg-emerald-500" : "bg-amber-500"}`} />
              {item.label}
              <span className="sr-only">{t(item.ready ? "common.yes" : "common.no")}</span>
            </li>
          ))}
        </ul>
        {!settings?.environment_capability ? <p className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs font-semibold text-amber-800 dark:border-amber-400/30 dark:bg-amber-500/15 dark:text-amber-100">{t("novaPoshta.environmentDisabledHelp")}</p> : null}
        <button
          className={`min-h-11 rounded-xl px-4 py-2 font-bold text-white disabled:cursor-not-allowed disabled:opacity-50 ${settings?.workspace_permission ? "bg-rose-600" : "bg-emerald-600"}`}
          disabled={isUpdatingPermission || (!settings?.workspace_permission && !activationPrerequisitesReady)}
          type="button"
          onClick={() => onUpdateWritePermission(!settings?.workspace_permission)}
        >
          {isUpdatingPermission
            ? t("novaPoshta.updatingPermission")
            : t(settings?.workspace_permission ? "novaPoshta.disableTtnCreation" : "novaPoshta.enableTtnCreation")}
        </button>
      </section>

      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
        <button className="min-h-11 rounded-xl border border-slate-300 px-4 py-2 font-bold disabled:opacity-60 dark:border-white/10" disabled={isTesting || !hasSavedKey} type="button" onClick={onTest}>{isTesting ? t("novaPoshta.testingConnection") : t("novaPoshta.testConnection")}</button>
        <button className="min-h-11 rounded-xl border border-rose-200 px-4 py-2 font-bold text-rose-700 disabled:opacity-60 dark:border-rose-400/40 dark:text-rose-200" disabled={isDisconnecting || !hasSavedKey} type="button" onClick={onDisconnect}>{isDisconnecting ? t("common.loading") : t("novaPoshta.disconnect")}</button>
      </div>
      {message ? <p className="rounded-xl bg-blue-50 p-3 text-sm font-semibold text-blue-700 dark:bg-blue-500/15 dark:text-blue-100">{message}</p> : null}
      <p className="text-xs text-slate-500 dark:text-slate-400">{t("novaPoshta.maskedCredentials")}</p>
    </section>
  );
}
