"use client";

import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { authStorage } from "@/services/auth.service";
import { disconnectMetaAds, fetchMetaAdsAccounts, fetchMetaAdsStatus, integrationErrorCode, selectMetaAdsAccount, startMetaAds, syncMetaAds } from "@/services/meta-ads";
import { clearAdsIntent, saveAdsIntent } from "@/features/integrations/lib/meta-ads-intent";

const input = "min-h-11 w-full min-w-0 rounded-lg border border-slate-300 px-3 dark:border-white/20 dark:bg-white/10";
const button = "min-h-11 rounded-xl border px-4 py-2 font-bold disabled:cursor-not-allowed disabled:opacity-50";

export function MetaAdsReadinessCard({ compact = false }: { compact?: boolean }) {
  const auth = useAuth();
  return <MetaAdsCard key={auth.currentWorkspaceId + ":" + auth.currentUser?.id} workspaceId={auth.currentWorkspaceId ?? ""} actorId={auth.currentUser?.id ?? ""} owner={auth.currentWorkspace?.role === "OWNER"} authenticated={auth.status === "authenticated"} compact={compact} />;
}
function MetaAdsCard({ workspaceId, actorId, owner, authenticated, compact }: { workspaceId: string; actorId: string; owner: boolean; authenticated: boolean; compact: boolean }) {
  const { t } = useI18n();
  const client = useQueryClient();
  const [pending, setPending] = useState(false);
  const busy = useRef(false);
  const [message, setMessage] = useState<string | null>(null);
  const [accountId, setAccountId] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [from, setFrom] = useState(new Date().toISOString().slice(0, 10));
  const [to, setTo] = useState(new Date().toISOString().slice(0, 10));
  const status = useQuery({ queryKey: ["meta-ads-status", workspaceId], queryFn: () => fetchMetaAdsStatus(workspaceId), enabled: authenticated && Boolean(workspaceId), retry: false });
  const accounts = useQuery({ queryKey: ["meta-ads-accounts", workspaceId], queryFn: () => fetchMetaAdsAccounts(workspaceId), enabled: owner && status.data?.connected === true, retry: false });
  const current = () => authStorage.getCurrentWorkspaceId() === workspaceId && authStorage.getCurrentActorId() === actorId;
  const errorText = (code: string) => {
    const translated = t("adsLive.errors." + code);
    return translated === "adsLive.errors." + code ? t("adsLive.errors.failed") : translated;
  };
  async function action(run: () => Promise<unknown>, success: string) {
    if (busy.current || !owner || !current()) return;
    busy.current = true;
    setPending(true); setMessage(null);
    try {
      await run();
      if (current()) {
        setMessage(t(success));
        await Promise.all([client.invalidateQueries({ queryKey: ["meta-ads-status", workspaceId] }), client.invalidateQueries({ queryKey: ["meta-ads-accounts", workspaceId] }), ... ["ad-campaigns", "ad-metrics", "ad-summary", "ad-performance", "ad-trend", "ad-crm-attribution", "dashboard"].map(key => client.invalidateQueries({ queryKey: [key, workspaceId] }))]);
      }
    } catch (error) {
      if (current()) {
        setMessage(errorText(integrationErrorCode(error)));
        void client.invalidateQueries({ queryKey: ["meta-ads-status", workspaceId] });
      }
    } finally { busy.current = false; if (current()) setPending(false); }
  }
  const data = status.data;
  const days = (Date.parse(to) - Date.parse(from)) / 86400000 + 1;
  const datesValid = Boolean(from && to && days >= 1 && days <= 91);
  return <section data-meta-ads-settings className="grid min-w-0 gap-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#15172A] dark:text-white sm:p-6">
    <div className="flex flex-col gap-2"><span className="text-xs font-semibold uppercase tracking-wider text-indigo-500">Meta Ads</span><h2 className="text-xl font-bold">{t("adsLive.callbackTitle")}</h2><p className="max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-300">{t("adsLive.source")}</p><p className="text-xs text-slate-500 dark:text-slate-400">{t("adsLive.providerFields")}</p></div>
    {status.isPending ? <p role="status">{t("common.loading")}</p> : null}
    {status.isError ? <p role="alert">{t("adsLive.loadFailed")} <button className={button} onClick={() => { void status.refetch(); }}>{t("adsLive.retry")}</button></p> : null}
    {data ? <>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3 dark:border-white/10"><span className="rounded-full border border-slate-300 px-3 py-1 text-sm font-semibold dark:border-white/20">{t("adsLive.statuses." + data.connection_status)}</span><span className="text-xs text-slate-500 dark:text-slate-400">{t("adsLive.lastSync")}: {data.last_synced_at ? new Date(data.last_synced_at).toLocaleString() : t("adsLive.never")}</span></div>
      {data.blockers?.length ? <ul className="grid gap-2 rounded-xl bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-500/10 dark:text-amber-100">{data.blockers.map(code => <li key={code}>{errorText(code)}</li>)}</ul> : null}
      {data.last_error_code ? <p role="alert">{errorText(data.last_error_code)}</p> : null}
      {!owner ? <p>{t("adsLive.ownerOnly")}</p> : <>
        <button className={button} disabled={pending || !data.can_connect} onClick={() => { void action(async () => {
          const result = await startMetaAds(workspaceId);
          if (!current()) return;
          const url = new URL(result.authorization_url);
          const state = url.searchParams.get("state");
          if (url.protocol !== "https:" || !(url.hostname === "facebook.com" || url.hostname.endsWith(".facebook.com")) || !state) throw new Error("invalid_authorization");
          saveAdsIntent({ actor: actorId, workspace: workspaceId, state, expires: result.state_expires_at, phase: "pending" });
          window.location.assign(url.href);
        }, "adsLive.redirecting"); }}>{t(data.connected || ["NEEDS_REAUTH", "TOKEN_EXPIRED", "PERMISSION_MISSING", "ERROR"].includes(data.connection_status) ? "adsLive.reconnect" : "adsLive.connect")}</button>
        {data.connected ? <section className="grid min-w-0 gap-3 rounded-xl border p-3">
          <h3 className="font-bold">{t("adsLive.accountTitle")}</h3>
          {data.account_name ? <p className="break-words">{data.account_name} · {data.currency} · {data.timezone}</p> : <p>{t("adsLive.selectionRequired")}</p>}
          {accounts.isFetching ? <p role="status">{t("common.loading")}</p> : null}
          {accounts.isError ? <p role="alert">{t("adsLive.accountsFailed")} <button className={button} onClick={() => { void accounts.refetch(); }}>{t("adsLive.retry")}</button></p> : null}
          {accounts.isSuccess && !accounts.data.accounts.length ? <p>{t("adsLive.noAccounts")}</p> : null}
          {accounts.data ? <>
            <p className="text-sm">{t("adsLive.currencyHelp", { currency: accounts.data.workspace_currency })}</p>
            <label className="grid min-w-0 gap-2 text-sm font-semibold"><span>{t("adsLive.accountTitle")}</span><select className={input} value={accountId} disabled={pending} onChange={event => setAccountId(event.target.value)}><option value="">{t("adsLive.chooseAccount")}</option>{accounts.data.accounts.map(account => <option key={account.external_account_id} value={account.external_account_id} disabled={!account.selectable}>{account.name} · {account.currency} · {account.timezone}{!account.selectable ? " — " + t("adsLive.currencyMismatch") : ""}</option>)}</select></label>
            <button className={button} disabled={pending || !accounts.data.accounts.some(account => account.external_account_id === accountId && account.selectable)} onClick={() => { void action(() => selectMetaAdsAccount(workspaceId, accountId), "adsLive.accountSaved"); }}>{t("adsLive.selectAccount")}</button>
          </> : null}
          {!compact ? <>
            <p className="text-sm">{t("adsLive.rangeHelp", { timezone: data.timezone ?? "—" })}</p>
            <div className="grid min-w-0 gap-3 sm:grid-cols-2">
              <label className="grid min-w-0 gap-2"><span>{t("adsLive.from")}</span><input className={input} type="date" value={from} disabled={pending} onChange={event => setFrom(event.target.value)} /></label>
              <label className="grid min-w-0 gap-2"><span>{t("adsLive.to")}</span><input className={input} type="date" value={to} disabled={pending} onChange={event => setTo(event.target.value)} /></label>
            </div>
            {!datesValid ? <p role="alert">{t("adsLive.errors.invalid_date_range")}</p> : null}
            <button className={button} disabled={pending || !data.can_sync || !datesValid} onClick={() => { void action(() => syncMetaAds(workspaceId, from, to), "adsLive.syncSuccess"); }}>{t(pending ? "common.loading" : "adsLive.sync")}</button>
            {!data.sync_enabled ? <p>{t("adsLive.errors.sync_disabled")}</p> : null}
          </> : null}
          <p className="text-sm">{t("adsLive.lastSync")}: {data.last_synced_at ? new Date(data.last_synced_at).toLocaleString() : t("adsLive.never")}</p>

        </section> : null}
        {data.connected || ["CONNECTING", "NEEDS_REAUTH", "TOKEN_EXPIRED", "PERMISSION_MISSING", "ERROR"].includes(data.connection_status) ? <div className="grid gap-2">
          <button className={button + " text-rose-700"} disabled={pending} onClick={() => setConfirm(true)}>{t("adsLive.disconnect")}</button>
          {confirm ? <div className="grid gap-2 rounded-xl border border-rose-300 p-3"><p>{t("adsLive.disconnectConfirm")}</p><button className={button} disabled={pending} onClick={() => { setConfirm(false); clearAdsIntent(); void action(() => disconnectMetaAds(workspaceId), "adsLive.disconnected"); }}>{t("adsLive.confirmDisconnect")}</button><button className={button} disabled={pending} onClick={() => setConfirm(false)}>{t("actions.cancel")}</button></div> : null}
        </div> : null}
      </>}
    </> : null}
    {message ? <p role="status" className="rounded-xl bg-blue-50 p-3 text-sm text-blue-900 dark:bg-blue-500/10 dark:text-blue-100">{message}</p> : null}
  </section>;
}
