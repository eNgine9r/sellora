"use client";

import { useI18n } from "@/i18n/provider";

export function MetaAdsReadinessCard() {
  const { t } = useI18n();

  return (
    <section className="grid gap-4 rounded-2xl bg-white p-5 shadow-sm dark:bg-[#15172A] dark:text-white" data-meta-ads-placeholder="manual-import-first">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-indigo-600">Meta Ads</p>
          <h2 className="mt-1 text-xl font-black">{t("metaAds.title")}</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{t("metaAds.subtitle")}</p>
        </div>
        <span className="w-fit rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800 dark:bg-amber-500/15 dark:text-amber-100">{t("metaAds.status")}</span>
      </div>

      <div className="grid gap-3 rounded-2xl border border-indigo-100 bg-indigo-50 p-4 text-sm text-indigo-950 dark:border-indigo-400/20 dark:bg-indigo-500/10 dark:text-indigo-100">
        <p className="font-bold">{t("metaAds.preparing")}</p>
        <p>{t("metaAds.manualImportSupported")}</p>
        <p>{t("metaAds.automaticLater")}</p>
      </div>

      <ul className="grid gap-2 text-sm text-slate-600 dark:text-slate-300">
        <li>• {t("metaAds.safeTokenRule")}</li>
        <li>• {t("metaAds.workspaceRule")}</li>
        <li>• {t("metaAds.ownerRule")}</li>
      </ul>
    </section>
  );
}
