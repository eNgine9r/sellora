"use client";

import Link from "next/link";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, Instagram, MessageCircle, Settings2 } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { fetchInstagramStatus, startInstagramConnect } from "@/services/meta-instagram";
import type { InstagramConnectionStatus } from "@/types/meta-instagram";

function statusTone(status: InstagramConnectionStatus | "DISCONNECTED", needsRepair: boolean): string {
  if (needsRepair) return "bg-amber-50 text-amber-800 dark:bg-amber-500/15 dark:text-amber-200";
  if (status === "CONNECTED") return "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300";
  if (status === "FAILED") return "bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300";
  return "bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-slate-300";
}

export function InstagramMessagingIntegrationCard({ workspaceId }: { workspaceId: string }) {
  const { t } = useI18n();
  const { currentWorkspace, status: authStatus } = useAuth();
  const canManage = currentWorkspace?.role === "OWNER";
  const canOpenDirect = canManage || currentWorkspace?.role === "MANAGER";
  const enabled = authStatus === "authenticated" && Boolean(workspaceId);
  const statusQuery = useQuery({
    queryKey: ["instagram-connection-status", workspaceId],
    queryFn: fetchInstagramStatus,
    enabled,
    retry: false,
  });
  const connectMutation = useMutation({
    mutationFn: startInstagramConnect,
    onSuccess: (data) => { window.location.assign(data.authorization_url); },
  });

  const data = statusQuery.data;
  const connected = data?.status === "CONNECTED";
  const needsRepair = Boolean(data && (
    (data.token_present && !data.webhook_active)
    || ["PERMISSION_MISSING", "TOKEN_EXPIRED", "WEBHOOK_INACTIVE", "RECONNECT_REQUIRED", "FAILED"].includes(data.status)
  ));
  const label = needsRepair
    ? t("integrationHub.needsAttention")
    : t("instagramSettings.status." + (data?.status ?? "DISCONNECTED"));
  const actions = connected && !needsRepair && canOpenDirect;
  const showConnect = !connected && canManage && !needsRepair;
  const primaryClass = "inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:opacity-60";

  return (
    <section className="relative grid w-full min-w-0 max-w-full content-start gap-4 overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#15172A] sm:p-6" data-instagram-integration-summary>
      <div className="absolute inset-x-0 top-0 h-1 bg-[linear-gradient(90deg,#f58529,#dd2a7b,#8134af,#515bd4)]" aria-hidden="true" />
      <div className="flex min-w-0 items-start gap-3">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-fuchsia-50 text-fuchsia-600 dark:bg-fuchsia-500/15 dark:text-fuchsia-300">
          <Instagram className="size-5" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">Instagram Direct</h2>
            {data ? <span className={"rounded-full px-2.5 py-1 text-[11px] font-semibold " + statusTone(data.status, needsRepair)}>{label}</span> : null}
          </div>
          <p className="mt-1 text-sm leading-5 text-slate-500 dark:text-slate-400">{t("integrationHub.instagramDescription")}</p>
        </div>
      </div>
      {statusQuery.isPending && enabled ? <p role="status" className="text-sm text-slate-500">{t("common.loading")}</p> : null}
      {statusQuery.isError ? <p role="alert" className="text-sm text-rose-600 dark:text-rose-300">{t("instagramSettings.profileFailed")}</p> : null}
      {connected && data?.instagram_username ? (
        <p className="min-w-0 truncate rounded-xl bg-slate-50 px-3 py-2 text-sm font-medium text-slate-800 dark:bg-white/5 dark:text-slate-200" title={"@" + data.instagram_username}>
          @{data.instagram_username}
        </p>
      ) : null}
      {data && !connected && !needsRepair ? <p className="text-sm leading-5 text-slate-500 dark:text-slate-400">{t("integrationHub.instagramConnectHint")}</p> : null}
      {needsRepair ? <p className="text-sm leading-5 text-amber-700 dark:text-amber-300">{t("integrationHub.instagramRepairHint")}</p> : null}
      {statusQuery.isError ? (
        <button type="button" onClick={() => { void statusQuery.refetch(); }} className={primaryClass}>{t("adsLive.retry")}</button>
      ) : actions ? (
        <Link href="/direct" className={primaryClass}><MessageCircle className="size-4" aria-hidden="true" />{t("integrationHub.openDirect")}<ArrowRight className="size-4" aria-hidden="true" /></Link>
      ) : showConnect ? (
        <button type="button" disabled={connectMutation.isPending} className={primaryClass} onClick={() => connectMutation.mutate()}>
          {t("instagramSettings.connect")}<ArrowRight className="size-4" aria-hidden="true" />
        </button>
      ) : data ? (
        <Link href="/settings/integrations/instagram" className={primaryClass}>
          {t(needsRepair ? "integrationHub.fixConnection" : "integrationHub.manageConnection")}<ArrowRight className="size-4" aria-hidden="true" />
        </Link>
      ) : null}
      {connectMutation.isError ? <p role="alert" className="text-sm text-rose-600 dark:text-rose-300">{t("integrationHub.connectError")}</p> : null}
      {(actions || showConnect) ? <div className="border-t border-slate-100 pt-3 dark:border-white/10">
        <Link href="/settings/integrations/instagram" className="inline-flex min-h-11 items-center gap-2 text-sm font-medium text-slate-500 hover:text-indigo-600 dark:text-slate-300 dark:hover:text-indigo-300">
          <Settings2 className="size-4" aria-hidden="true" />{t("integrationHub.manageConnection")}
        </Link>
      </div> : null}
    </section>
  );
}
