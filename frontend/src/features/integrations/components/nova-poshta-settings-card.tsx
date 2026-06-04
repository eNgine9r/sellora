"use client";
import { FormEvent, useEffect, useState } from "react";
import { IntegrationStatusBadge } from "@/features/integrations/components/integration-status-badge";
import { NovaPoshtaSettings, NovaPoshtaSettingsPayload } from "@/types/integrations";

export function NovaPoshtaSettingsCard({ settings, message, onSave, onTest, onDisconnect }: { settings?: NovaPoshtaSettings; message?: string | null; onSave: (payload: NovaPoshtaSettingsPayload) => void; onTest: () => void; onDisconnect: () => void }) {
  const [apiKey, setApiKey] = useState("");
  const [senderCityRef, setSenderCityRef] = useState(settings?.sender_city_ref ?? "");
  const [senderWarehouseRef, setSenderWarehouseRef] = useState(settings?.sender_warehouse_ref ?? "");
  const [senderCounterpartyRef, setSenderCounterpartyRef] = useState(settings?.sender_counterparty_ref ?? "");
  const [senderContactRef, setSenderContactRef] = useState(settings?.sender_contact_ref ?? "");
  const [senderPhone, setSenderPhone] = useState(settings?.sender_phone ?? "");

  useEffect(() => {
    setSenderCityRef(settings?.sender_city_ref ?? "");
    setSenderWarehouseRef(settings?.sender_warehouse_ref ?? "");
    setSenderCounterpartyRef(settings?.sender_counterparty_ref ?? "");
    setSenderContactRef(settings?.sender_contact_ref ?? "");
    setSenderPhone(settings?.sender_phone ?? "");
  }, [settings]);
  function submit(event: FormEvent) { event.preventDefault(); onSave({ api_key: apiKey, sender_city_ref: senderCityRef || null, sender_warehouse_ref: senderWarehouseRef || null, sender_counterparty_ref: senderCounterpartyRef || null, sender_contact_ref: senderContactRef || null, sender_phone: senderPhone || null }); setApiKey(""); }
  return <section className="grid gap-4 rounded-2xl bg-white p-5 shadow-sm"><div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="text-xl font-black">Nova Poshta</h2><p className="text-sm text-slate-500">Connect delivery directory search and TTN creation.</p></div><IntegrationStatusBadge status={settings?.status ?? "DISCONNECTED"} /></div>{settings?.masked_api_key ? <p className="rounded-xl bg-slate-50 p-3 text-sm">Saved key: <strong>{settings.masked_api_key}</strong></p> : null}<form className="grid gap-3" onSubmit={submit}><input className="min-h-11 rounded-lg border border-slate-300 px-3" type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder="Nova Poshta API key" required /><div className="grid gap-3 md:grid-cols-2"><input className="min-h-11 rounded-lg border border-slate-300 px-3" value={senderCityRef} onChange={(event) => setSenderCityRef(event.target.value)} placeholder="Sender city ref" /><input className="min-h-11 rounded-lg border border-slate-300 px-3" value={senderWarehouseRef} onChange={(event) => setSenderWarehouseRef(event.target.value)} placeholder="Sender warehouse ref" /><input className="min-h-11 rounded-lg border border-slate-300 px-3" value={senderCounterpartyRef} onChange={(event) => setSenderCounterpartyRef(event.target.value)} placeholder="Sender counterparty ref" /><input className="min-h-11 rounded-lg border border-slate-300 px-3" value={senderContactRef} onChange={(event) => setSenderContactRef(event.target.value)} placeholder="Sender contact ref" /><input className="min-h-11 rounded-lg border border-slate-300 px-3" value={senderPhone} onChange={(event) => setSenderPhone(event.target.value)} placeholder="Sender phone" /></div><button className="min-h-11 rounded-xl bg-blue-600 px-4 py-2 font-bold text-white" type="submit">Save API key</button></form><div className="flex flex-wrap gap-2"><button className="min-h-11 rounded-xl border border-slate-300 px-4 py-2 font-bold" onClick={onTest}>Test connection</button><button className="min-h-11 rounded-xl border border-rose-200 px-4 py-2 font-bold text-rose-700" onClick={onDisconnect}>Disconnect</button></div>{message ? <p className="rounded-xl bg-blue-50 p-3 text-sm font-semibold text-blue-700">{message}</p> : null}<p className="text-xs text-slate-500">Sender settings are required before TTN creation. Saved API keys are masked and never displayed raw.</p></section>;
}
