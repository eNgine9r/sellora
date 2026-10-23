"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, ArrowRight, Check, ChevronDown, LoaderCircle, Megaphone, Settings2, ShieldCheck } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { authStorage } from "@/services/auth.service";
import {
  disconnectMetaAds,
  fetchMetaAdsAccounts,
  fetchMetaAdsStatus,
  integrationErrorCode,
  selectMetaAdsAccount,
  startMetaAds,
  syncMetaAds,
} from "@/services/meta-ads";
import { clearAdsIntent, saveAdsIntent } from "@/features/integrations/lib/meta-ads-intent";

const primary = "inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:cursor-not-allowed disabled:opacity-50";
const secondary = "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/15 dark:text-slate-100 dark:hover:bg-white/10";
const field = "min-h-11 w-full min-w-0 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-white/15 dark:bg-white/10 dark:text-white";
const subdued = "text-sm leading-6 text-slate-500 dark:text-slate-400";
const repairStatuses = ["NEEDS_REAUTH", "TOKEN_EXPIRED", "PERMISSION_MISSING", "ERROR"];

export function MetaAdsReadinessCard({ compact = false }: { compact?: boolean }) {
  const auth = useAuth();
  return (
    <MetaAdsCard
      key={(auth.currentWorkspaceId ?? "") + ":" + (auth.currentUser?.id ?? "")}
      workspaceId={auth.currentWorkspaceId ?? ""}
      actorId={auth.currentUser?.id ?? ""}
      owner={auth.currentWorkspace?.role === "OWNER"}
      authenticated={auth.status === "authenticated"}
      compact={compact}
    />
  );
}

function MetaAdsCard({
  workspaceId, actorId, owner, authenticated, compact,
}: {
  workspaceId: string; actorId: string; owner: boolean; authenticated: boolean; compact: boolean;
}) {
  const { t } = useI18n();
  const client = useQueryClient();
  const busy = useRef(false);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [accountId, setAccountId] = useState("");
  const [editAccount, setEditAccount] = useState(false);
  const [showSync, setShowSync] = useState(false);
  const [syncReview, setSyncReview] = useState(false);
  const [confirmDisconnect, setConfirmDisconnect] = useState(false);
  const [from, setFrom] = useState(new Date().toISOString().slice(0, 10));
  const [to, setTo] = useState(new Date().toISOString().slice(0, 10));

  const status = useQuery({
    queryKey: ["meta-ads-status", workspaceId],
    queryFn: () => fetchMetaAdsStatus(workspaceId),
    enabled: authenticated && Boolean(workspaceId),
    retry: false,
  });
  const data = status.data;
  const needsAccount = Boolean(data?.connected && (data.account_selection_required || !data.account_name));
  const accounts = useQuery({
    queryKey: ["meta-ads-accounts", workspaceId],
    queryFn: () => fetchMetaAdsAccounts(workspaceId),
    enabled: owner && Boolean(data?.connected) && (needsAccount || editAccount),
    retry: false,
  });

  const current = () => authStorage.getCurrentWorkspaceId() === workspaceId && authStorage.getCurrentActorId() === actorId;
  const errorText = (code: string) => {
    const translated = t("adsLive.errors." + code);
    return translated === "adsLive.errors." + code ? t("adsLive.errors.failed") : translated;
  };

  async function action(run: () => Promise<unknown>, success: string) {
    if (busy.current || !owner || !current()) return;
    busy.current = true;
    setPending(true);
    setMessage(null);
    try {
      await run();
      if (current()) {
        setMessage(t(success));
        await Promise.all([
          client.invalidateQueries({ queryKey: ["meta-ads-status", workspaceId] }),
          client.invalidateQueries({ queryKey: ["meta-ads-accounts", workspaceId] }),
          ...["ad-campaigns", "ad-metrics", "ad-summary", "ad-performance", "ad-trend", "ad-crm-attribution", "dashboard"]
            .map(key => client.invalidateQueries({ queryKey: [key, workspaceId] })),
        ]);
      }
    } catch (error) {
      if (current()) {
        setMessage(errorText(integrationErrorCode(error)));
        void client.invalidateQueries({ queryKey: ["meta-ads-status", workspaceId] });
      }
    } finally {
      busy.current = false;
      if (current()) setPending(false);
    }
  }

  const days = (Date.parse(to) - Date.parse(from)) / 86400000 + 1;
  const datesValid = Boolean(from && to && days >= 1 && days <= 91);
  const selected = accounts.data?.accounts.find(account => account.external_account_id === accountId && account.selectable);
  const connected = Boolean(data?.connected);
  const canConnect = Boolean(data?.can_connect);
  const canSync = Boolean(data?.can_sync);
  const needsRepair = Boolean(data && repairStatuses.includes(data.connection_status));
  const hasProblems = Boolean(data?.blockers?.length || data?.last_error_code);
  const statusStyle = connected
    ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300"
    : needsRepair
      ? "bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300"
      : "bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-slate-300";

  async function beginOAuth() {
    await action(async () => {
      const result = await startMetaAds(workspaceId);
      if (!current()) return;
      const url = new URL(result.authorization_url);
      const state = url.searchParams.get("state");
      if (url.protocol !== "https:" ||
        !(url.hostname === "facebook.com" || url.hostname.endsWith(".facebook.com")) || !state) {
        throw new Error("invalid_authorization");
      }
      saveAdsIntent({ actor: actorId, workspace: workspaceId, state, expires: result.state_expires_at, phase: "pending" });
      window.location.assign(url.href);
    }, "adsLive.redirecting");
  }

  function accountPicker() {
    return (
      <div className="grid gap-3" data-meta-ads-account-selection>
        {accounts.isFetching ? <p className={subdued} role="status">{t("common.loading")}</p> : null}
        {accounts.isError ? (
          <div className="grid gap-2" role="alert">
            <p className={subdued}>{t("adsLive.accountsFailed")}</p>
            <button className={secondary} type="button" onClick={() => { void accounts.refetch(); }}>{t("adsLive.retry")}</button>
          </div>
        ) : null}
        {accounts.isSuccess && accounts.data.accounts.length === 0 ? <p className={subdued}>{t("adsLive.noAccounts")}</p> : null}
        {accounts.data && accounts.data.accounts.length > 0 ? (
          <>
            <label className="grid gap-2 text-sm font-medium text-slate-700 dark:text-slate-200">
              {t("adsLive.accountTitle")}
              <select
                className={field}
                value={accountId}
                disabled={pending}
                onChange={event => { setAccountId(event.target.value); setSyncReview(false); }}
              >
                <option value="">{t("adsLive.chooseAccount")}</option>
                {accounts.data.accounts.map(account => (
                  <option
                    key={account.external_account_id}
                    value={account.external_account_id}
                    disabled={!account.selectable}
                  >
                    {account.name} · {account.currency}{!account.selectable ? " — " + t("adsLive.currencyMismatch") : ""}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className={primary}
              disabled={pending || !selected}
              onClick={() => {
                if (!selected) return;
                setSyncReview(false);
                void action(() => selectMetaAdsAccount(workspaceId, selected.external_account_id), "adsLive.accountSaved")
                  .then(() => { if (current()) setEditAccount(false); });
              }}
            >
              {t("adsLive.selectAccount")} <ArrowRight className="size-4" aria-hidden="true" />
            </button>
          </>
        ) : null}
      </div>
    );
  }

  return (
    <section
      data-meta-ads-settings
      className="relative grid min-w-0 content-start gap-4 overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#15172A] sm:p-6"
    >
      <div className="flex min-w-0 items-start gap-3">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-300">
          <Megaphone className="size-5" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">Meta Ads</h2>
            {data ? (
              <span className={"rounded-full px-2.5 py-1 text-[11px] font-semibold " + statusStyle}>
                {t("adsLive.statuses." + data.connection_status)}
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-sm leading-5 text-slate-500 dark:text-slate-400">{t("adsLive.simple.description")}</p>
        </div>
      </div>

      {status.isPending ? (
        <p role="status" className={"flex items-center gap-2 " + subdued}>
          <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />{t("common.loading")}
        </p>
      ) : null}

      {status.isError ? (
        <div role="alert" className="grid gap-3">
          <p className={subdued}>{t("adsLive.loadFailed")}</p>
          <button className={secondary} type="button" onClick={() => { void status.refetch(); }}>{t("adsLive.retry")}</button>
        </div>
      ) : null}

      {data ? (
        <>
          {connected && data.account_name && !needsAccount ? (
            <div className="rounded-xl border border-slate-100 bg-slate-50/80 px-4 py-3 dark:border-white/10 dark:bg-white/5" data-meta-ads-current-account>
              <div className="flex items-start gap-2">
                <Check className="mt-0.5 size-4 shrink-0 text-emerald-600" aria-hidden="true" />
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-slate-900 dark:text-white" title={data.account_name}>{data.account_name}</p>
                  <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                    {[data.currency, data.timezone].filter(Boolean).join(" · ")}
                  </p>
                </div>
              </div>
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                {t("adsLive.lastSync")}: {data.last_synced_at ? new Date(data.last_synced_at).toLocaleString() : t("adsLive.never")}
              </p>
            </div>
          ) : null}

          {needsAccount && owner ? (
            <div className="grid gap-3 rounded-xl border border-indigo-100 bg-indigo-50/40 p-4 dark:border-indigo-400/15 dark:bg-indigo-400/5">
              <p className="text-sm font-semibold text-slate-900 dark:text-white">{t("adsLive.simple.chooseTitle")}</p>
              <p className={subdued}>{t("adsLive.simple.chooseHelp")}</p>
              {accountPicker()}
            </div>
          ) : null}

          {!owner ? (
            <p className={subdued}>{t("adsLive.ownerOnly")}</p>
          ) : !connected ? (
            canConnect ? (
              <button className={primary} type="button" disabled={pending} onClick={() => { void beginOAuth(); }}>
                {pending ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : null}
                {t(needsRepair ? "adsLive.reconnect" : "adsLive.connect")}
                <ArrowRight className="size-4" aria-hidden="true" />
              </button>
            ) : (
              <div className="grid gap-3" data-meta-ads-setup-pending>
                <p className={subdued}>{t("adsLive.simple.notReady")}</p>
                <Link className={primary} href="/advertising">
                  {t("adsLive.simple.openAdvertising")} <ArrowRight className="size-4" aria-hidden="true" />
                </Link>
              </div>
            )
          ) : !needsAccount ? (
            canSync && !compact ? (
              <div className="grid gap-3">
                {!showSync ? (
                  <button className={primary} type="button" disabled={pending} onClick={() => setShowSync(true)}>
                    {t("adsLive.simple.updateMetrics")} <ArrowRight className="size-4" aria-hidden="true" />
                  </button>
                ) : (
                  <div className="grid gap-3 rounded-xl border border-slate-200 p-4 dark:border-white/15" data-meta-ads-sync-form>
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="text-sm font-semibold text-slate-900 dark:text-white">{t("adsLive.simple.periodTitle")}</h3>
                      <button className="text-xs font-semibold text-indigo-600 hover:underline dark:text-indigo-300" type="button" onClick={() => { setShowSync(false); setSyncReview(false); }} disabled={pending}>
                        {t("actions.cancel")}
                      </button>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{t("adsLive.simple.timezoneHelp", { timezone: data.timezone ?? "—" })}</p>
                    <div className="grid min-w-0 gap-3 sm:grid-cols-2">
                      <label className="grid min-w-0 gap-1.5 text-xs font-medium text-slate-700 dark:text-slate-200">
                        {t("adsLive.from")}
                        <input className={field} type="date" value={from} disabled={pending} onChange={event => { setFrom(event.target.value); setSyncReview(false); }} />
                      </label>
                      <label className="grid min-w-0 gap-1.5 text-xs font-medium text-slate-700 dark:text-slate-200">
                        {t("adsLive.to")}
                        <input className={field} type="date" value={to} disabled={pending} onChange={event => { setTo(event.target.value); setSyncReview(false); }} />
                      </label>
                    </div>
                    {!datesValid ? <p className="text-xs text-rose-600" role="alert">{t("adsLive.errors.invalid_date_range")}</p> : null}
                    {!syncReview ? (
                      <button type="button" className={primary} disabled={pending || !datesValid} onClick={() => setSyncReview(true)}>
                        {t("adsLive.reviewSync")}
                      </button>
                    ) : (
                      <div className="grid gap-3 rounded-xl bg-indigo-50 p-3 text-sm dark:bg-indigo-500/10" data-meta-ads-sync-review>
                        <h4 className="font-semibold text-slate-900 dark:text-white">{t("adsLive.syncReviewTitle")}</h4>
                        <p className={subdued}>{data.account_name} · {from} — {to}</p>
                        <p className="text-xs leading-5 text-slate-500 dark:text-slate-300">{t("adsLive.syncReviewNotice")}</p>
                        <button className={primary} type="button" disabled={pending || !datesValid} onClick={() => {
                          setSyncReview(false);
                          void action(() => syncMetaAds(workspaceId, from, to), "adsLive.syncSuccess")
                            .then(() => { if (current()) setShowSync(false); });
                        }}>
                          {pending ? t("common.loading") : t("adsLive.confirmSync")}
                        </button>
                        <button className={secondary} type="button" disabled={pending} onClick={() => setSyncReview(false)}>{t("actions.cancel")}</button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : !canSync ? (
              <p className={subdued}>{t("adsLive.simple.syncPending")}</p>
            ) : null
          ) : null}

          {message ? (
            <p role="status" className="rounded-xl bg-indigo-50 p-3 text-sm text-indigo-900 dark:bg-indigo-500/10 dark:text-indigo-200">{message}</p>
          ) : null}

          <div className="flex items-center gap-2 border-t border-slate-100 pt-3 text-xs text-slate-500 dark:border-white/10 dark:text-slate-400">
            <ShieldCheck className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
            <span>{t("adsLive.simple.safety")}</span>
          </div>

          {(hasProblems || (connected && owner)) ? (
            <details className="group border-t border-slate-100 pt-3 dark:border-white/10" data-meta-ads-advanced>
              <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-2 rounded-lg text-sm font-medium text-slate-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500 dark:text-slate-300 [&::-webkit-details-marker]:hidden">
                <span className="inline-flex items-center gap-2">
                  {hasProblems ? <AlertCircle className="size-4" aria-hidden="true" /> : <Settings2 className="size-4" aria-hidden="true" />}
                  {t(hasProblems ? "adsLive.simple.whyUnavailable" : "adsLive.simple.connectionSettings")}
                </span>
                <ChevronDown className="size-4 transition-transform group-open:rotate-180" aria-hidden="true" />
              </summary>
              <div className="grid gap-3 pb-2 pt-2">
                {data.blockers?.length ? (
                  <ul className="grid gap-1.5 text-xs leading-5 text-slate-600 dark:text-slate-300">
                    {Array.from(new Set(data.blockers)).map(code => <li key={code}>{errorText(code)}</li>)}
                  </ul>
                ) : null}
                {data.last_error_code ? <p className="text-xs text-rose-600 dark:text-rose-300">{errorText(data.last_error_code)}</p> : null}
                {connected && owner ? (
                  <>
                    {!needsAccount ? (
                      <button className={secondary} type="button" disabled={pending} onClick={() => setEditAccount(value => !value)}>
                        {t("adsLive.simple.changeAccount")}
                      </button>
                    ) : null}
                    {editAccount && !needsAccount ? accountPicker() : null}
                    <button className={secondary + " text-rose-700 dark:text-rose-300"} type="button" disabled={pending} onClick={() => setConfirmDisconnect(true)}>
                      {t("adsLive.disconnect")}
                    </button>
                    {confirmDisconnect ? (
                      <div className="grid gap-3 rounded-xl border border-rose-200 p-3 dark:border-rose-500/25">
                        <p className={subdued}>{t("adsLive.disconnectConfirm")}</p>
                        <button className={primary + " bg-rose-600 hover:bg-rose-700"} type="button" disabled={pending} onClick={() => {
                          setConfirmDisconnect(false);
                          clearAdsIntent();
                          void action(() => disconnectMetaAds(workspaceId), "adsLive.disconnected");
                        }}>{t("adsLive.confirmDisconnect")}</button>
                        <button className={secondary} type="button" disabled={pending} onClick={() => setConfirmDisconnect(false)}>{t("actions.cancel")}</button>
                      </div>
                    ) : null}
                  </>
                ) : null}
              </div>
            </details>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
