"use client";

import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/hooks/use-auth";
import { safeApiErrorMessage } from "@/services/api";
import { fetchWorkspaceSettings, updateWorkspaceSettings, CurrencyCode } from "@/services/workspaces";

export default function WorkspaceSettingsPage() {
  const queryClient = useQueryClient();
  const { currentWorkspaceId, currentWorkspace, reloadCurrentUser } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [currencyCode, setCurrencyCode] = useState<CurrencyCode>("UAH");
  const [timezone, setTimezone] = useState("Europe/Kyiv");
  const [message, setMessage] = useState<string | null>(null);
  const canManage = currentWorkspace?.role === "OWNER";
  const settings = useQuery({ queryKey: ["workspace-settings", workspaceId], queryFn: () => fetchWorkspaceSettings(workspaceId), enabled: Boolean(workspaceId) });
  const save = useMutation({
    mutationFn: () => updateWorkspaceSettings(workspaceId, { name, slug, currency_code: currencyCode, timezone }),
    onSuccess: async () => { setMessage("Налаштування робочого простору оновлено."); await queryClient.invalidateQueries({ queryKey: ["workspace-settings", workspaceId] }); await reloadCurrentUser(); },
    onError: (error) => setMessage(safeApiErrorMessage(error, "Не вдалося зберегти налаштування робочого простору.")),
  });
  useEffect(() => { if (settings.data) { setName(settings.data.name); setSlug(settings.data.slug); setCurrencyCode(settings.data.currency_code); setTimezone(settings.data.timezone); } }, [settings.data]);
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (canManage) save.mutate(); }
  return <main className="min-h-screen bg-[#F8F7FC] p-4 text-slate-950 sm:p-6"><div className="mx-auto max-w-4xl rounded-[28px] bg-white p-6 shadow-[0_18px_45px_rgba(15,23,42,0.06)] sm:p-8">
    <p className="text-sm font-bold uppercase tracking-[0.25em] text-violet-600">Налаштування</p><h1 className="mt-3 text-4xl font-black">Робочий простір</h1><p className="mt-3 text-slate-600">Керування налаштуваннями поточного магазину.</p>
    {!canManage ? <p className="mt-5 rounded-2xl bg-amber-50 px-4 py-3 text-sm font-bold text-amber-700">У вас немає доступу до керування робочим простором.</p> : null}
    {settings.isLoading ? <p className="mt-5 text-sm text-slate-500">Завантаження налаштувань…</p> : null}
    <form className="mt-6 grid gap-4" onSubmit={submit}>
      <label className="grid gap-1 text-sm font-bold">Назва магазину<input className="min-h-11 rounded-xl border border-slate-300 px-3 disabled:bg-slate-50" value={name} onChange={(e) => setName(e.target.value)} disabled={!canManage || save.isPending} required /></label>
      <label className="grid gap-1 text-sm font-bold">Slug / коротка назва<input className="min-h-11 rounded-xl border border-slate-300 px-3 disabled:bg-slate-50" value={slug} onChange={(e) => setSlug(e.target.value)} disabled={!canManage || save.isPending} required pattern="[a-z0-9]+(-[a-z0-9]+)*" /></label>
      <div className="grid gap-4 sm:grid-cols-2"><label className="grid gap-1 text-sm font-bold">Валюта<select className="min-h-11 rounded-xl border border-slate-300 px-3 disabled:bg-slate-50" value={currencyCode} onChange={(e) => setCurrencyCode(e.target.value as CurrencyCode)} disabled={!canManage || save.isPending}><option value="UAH">UAH — гривня</option><option value="USD">USD — долар США</option></select></label>
      <label className="grid gap-1 text-sm font-bold">Часовий пояс<input className="min-h-11 rounded-xl border border-slate-300 px-3 disabled:bg-slate-50" value={timezone} onChange={(e) => setTimezone(e.target.value)} disabled={!canManage || save.isPending} required /></label></div>
      {settings.isError ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm font-bold text-red-700">Не вдалося завантажити робочий простір.</p> : null}{message ? <p className="rounded-2xl bg-violet-50 px-4 py-3 text-sm font-bold text-violet-700">{message}</p> : null}
      <button className="min-h-11 rounded-2xl bg-violet-600 px-5 font-black text-white disabled:opacity-50" disabled={!canManage || save.isPending}>{save.isPending ? "Збереження…" : "Зберегти зміни"}</button>
    </form></div></main>;
}
