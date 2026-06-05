"use client";

import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/hooks/use-auth";
import { safeApiErrorMessage } from "@/services/api";
import { fetchWorkspaceSettings, updateWorkspaceSettings } from "@/services/workspaces";

const cards = [
  {
    title: "Import Center",
    description: "Upload Excel or CSV files, preview rows, validate mappings, and import historical data.",
    href: "/settings/import",
    action: "Open Import Center",
    badge: "Data tools",
  },
  {
    title: "Integrations",
    description: "Connect delivery and external services such as Nova Poshta.",
    href: "/settings/integrations",
    action: "Open Integrations",
    badge: "Connections",
  },
  {
    title: "Nova Poshta",
    description: "Configure Nova Poshta credentials, sender settings, cities, warehouses, and TTN creation.",
    href: "/settings/integrations",
    action: "Configure Nova Poshta",
    badge: "Delivery",
  },
];

export default function Page() {
  const queryClient = useQueryClient();
  const { currentUser, currentWorkspace, currentWorkspaceId, reloadCurrentUser, status } = useAuth();
  const workspaceId = currentWorkspaceId ?? "";
  const enabled = status === "authenticated" && Boolean(currentUser) && Boolean(workspaceId);
  const canUpdateWorkspace = currentWorkspace?.role === "OWNER";
  const [name, setName] = useState("");
  const [currencyCode, setCurrencyCode] = useState<"UAH" | "USD">("UAH");
  const [message, setMessage] = useState<string | null>(null);
  const settings = useQuery({ queryKey: ["workspace-settings", workspaceId], queryFn: () => fetchWorkspaceSettings(workspaceId), enabled });
  const saveSettings = useMutation({
    mutationFn: () => updateWorkspaceSettings(workspaceId, { name, currency_code: currencyCode }),
    onSuccess: async () => {
      setMessage("Workspace settings saved.");
      queryClient.invalidateQueries({ queryKey: ["workspace-settings", workspaceId] });
      await reloadCurrentUser();
    },
    onError: (error) => setMessage(safeApiErrorMessage(error, "Unable to save workspace settings.")),
  });

  useEffect(() => {
    if (settings.data) {
      setName(settings.data.name);
      setCurrencyCode(settings.data.currency_code);
    }
  }, [settings.data]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canUpdateWorkspace) return;
    setMessage(null);
    saveSettings.mutate();
  }

  return (
    <main className="min-h-screen min-w-0 overflow-x-hidden bg-[#F8F7FC] p-4 text-slate-950 sm:p-6">
      <div className="mx-auto grid min-w-0 max-w-6xl gap-6">
        <section className="min-w-0 rounded-[28px] bg-white p-6 shadow-[0_18px_45px_rgba(15,23,42,0.06)] sm:p-8">
          <p className="text-sm font-bold uppercase tracking-[0.25em] text-violet-600">Sellora</p>
          <h1 className="mt-3 text-4xl font-black text-slate-950">Settings</h1>
          <p className="mt-3 max-w-2xl text-slate-600">Manage workspace tools, import workflows, and external service integrations from one place.</p>
        </section>
        <section className="rounded-[24px] bg-white p-5 shadow-[0_18px_45px_rgba(15,23,42,0.06)]">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <span className="w-fit rounded-full bg-violet-50 px-3 py-1 text-xs font-black uppercase tracking-[0.18em] text-violet-700">Workspace</span>
              <h2 className="mt-3 text-2xl font-black text-slate-950">Workspace settings</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Currency controls how financial values are displayed across Sellora. It does not convert historical amounts.</p>
            </div>
            {!canUpdateWorkspace ? <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-500">Owner-only</span> : null}
          </div>
          <form className="mt-5 grid gap-4 md:grid-cols-[1fr_260px_auto]" onSubmit={submit}>
            <label className="grid min-w-0 gap-1 text-sm font-semibold text-slate-700">Workspace name
              <input className="min-h-11 rounded-xl border border-slate-300 px-3 py-2 disabled:bg-slate-50" disabled={!canUpdateWorkspace} value={name} onChange={(event) => setName(event.target.value)} />
            </label>
            <label className="grid min-w-0 gap-1 text-sm font-semibold text-slate-700">Currency
              <select className="min-h-11 rounded-xl border border-slate-300 px-3 py-2 disabled:bg-slate-50" disabled={!canUpdateWorkspace} value={currencyCode} onChange={(event) => setCurrencyCode(event.target.value as "UAH" | "USD")}>
                <option value="UAH">UAH — Ukrainian hryvnia</option>
                <option value="USD">USD — US dollar</option>
              </select>
            </label>
            <button className="min-h-11 self-end rounded-2xl bg-violet-600 px-5 py-3 text-sm font-bold text-white transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-50" disabled={!canUpdateWorkspace || saveSettings.isPending} type="submit">Save settings</button>
          </form>
          {message ? <p className="mt-3 rounded-lg bg-violet-50 px-3 py-2 text-sm font-semibold text-violet-700">{message}</p> : null}
        </section>
        <section className="grid min-w-0 gap-4 md:grid-cols-3">
          {cards.map((card) => (
            <article key={card.title} className="flex min-h-64 flex-col justify-between rounded-[24px] bg-white p-5 shadow-[0_18px_45px_rgba(15,23,42,0.06)]">
              <div className="grid min-w-0 gap-3">
                <span className="w-fit rounded-full bg-violet-50 px-3 py-1 text-xs font-black uppercase tracking-[0.18em] text-violet-700">{card.badge}</span>
                <h2 className="text-2xl font-black text-slate-950">{card.title}</h2>
                <p className="text-sm leading-6 text-slate-600">{card.description}</p>
              </div>
              <a className="mt-6 inline-flex min-h-11 items-center justify-center rounded-2xl bg-violet-600 px-5 py-3 text-sm font-bold text-white transition hover:bg-violet-700" href={card.href}>{card.action}</a>
            </article>
          ))}
        </section>
      </div>
    </main>
  );
}
