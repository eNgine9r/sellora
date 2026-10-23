"use client";

import Link from "next/link";
import { ArrowRight, PackageCheck, Settings2, Truck } from "lucide-react";
import { useI18n } from "@/i18n/provider";
import type { NovaPoshtaSettings } from "@/types/integrations";

export function NovaPoshtaOverviewCard({
  settings, loading, error,
}: {
  settings?: NovaPoshtaSettings; loading?: boolean; error?: boolean;
}) {
  const { t } = useI18n();
  const connected = settings?.status === "CONNECTED" && Boolean(settings.masked_api_key);
  const ready = Boolean(connected && settings?.provider_writes_enabled);
  const needsSetup = Boolean(connected && !ready);
  const label = ready ? t("integrationHub.ready") : needsSetup ? t("integrationHub.needsSetup") : t("integrationHub.notConnected");
  const badgeTone = ready ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300"
    : needsSetup ? "bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300"
      : "bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-slate-300";
  const primaryClass = "inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500";
  return (
    <section className="relative grid min-w-0 content-start gap-4 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#15172A] sm:p-6" data-nova-poshta-integration-summary>
      <div className="flex min-w-0 items-start gap-3">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-sky-50 text-sky-600 dark:bg-sky-500/15 dark:text-sky-300">
          <Truck className="size-5" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">{t("novaPoshta.title")}</h2>
            {!loading && !error ? <span className={"rounded-full px-2.5 py-1 text-[11px] font-semibold " + badgeTone}>{label}</span> : null}
          </div>
          <p className="mt-1 text-sm leading-5 text-slate-500 dark:text-slate-400">{t("integrationHub.novaDescription")}</p>
        </div>
      </div>
      {loading ? <p role="status" className="text-sm text-slate-500">{t("common.loading")}</p> : null}
      {error ? <p role="alert" className="text-sm text-rose-600 dark:text-rose-300">{t("integrationHub.statusUnavailable")}</p> : null}
      {!loading && !error ? (
        <p className="text-sm leading-5 text-slate-500 dark:text-slate-400">
          {t(ready ? "integrationHub.novaReadyHint" : needsSetup ? "integrationHub.novaSetupHint" : "integrationHub.novaConnectHint")}
        </p>
      ) : null}
      {!loading ? (
        <Link href={ready ? "/shipments" : "/settings/integrations/nova-poshta"} className={primaryClass}>
          {ready ? <PackageCheck className="size-4" aria-hidden="true" /> : null}
          {t(ready ? "integrationHub.openShipments" : needsSetup ? "integrationHub.completeSetup" : "integrationHub.connectNova")}
          <ArrowRight className="size-4" aria-hidden="true" />
        </Link>
      ) : null}
      <div className="border-t border-slate-100 pt-3 dark:border-white/10">
        <Link href="/settings/integrations/nova-poshta" className="inline-flex min-h-11 items-center gap-2 text-sm font-medium text-slate-500 hover:text-indigo-600 dark:text-slate-300 dark:hover:text-indigo-300">
          <Settings2 className="size-4" aria-hidden="true" />{t("integrationHub.manageConnection")}
        </Link>
      </div>
    </section>
  );
}
