"use client";

import { featureGates } from "@/config/feature-gates";
import { useI18n } from "@/i18n/provider";

const previewStatuses = [
  "WOULD_CREATE",
  "WOULD_UPDATE",
  "WOULD_SKIP",
  "POTENTIAL_CONFLICT",
  "NEEDS_EXTERNAL_ID_SUPPORT",
  "INVALID",
] as const;

export function MetaAdsReadinessCard({ compact = false }: { compact?: boolean }) {
  const { t } = useI18n();

  return (
    <section
      className="grid gap-4 rounded-2xl bg-white p-5 shadow-sm dark:bg-[#15172A] dark:text-white"
      data-meta-ads-placeholder="manual-import-first"
      data-meta-ads-sync-preview-enabled={String(featureGates.metaAdsSyncPreviewEnabled)}
      data-meta-ads-no-live-connection="true"
      data-meta-ads-no-apply-run="true"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-indigo-600">Meta Ads</p>
          <h2 className="mt-1 text-xl font-black">{t("metaAds.notActiveTitle")}</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{t("metaAds.currentSourceCopy")}</p>
          <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{t("metaAds.futureSyncCopy")}</p>
          <p className="mt-2 text-sm leading-6 font-semibold text-slate-800 dark:text-slate-100">{t("metaAds.selloraSideCopy")}</p>
        </div>
        <span className="w-fit rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800 dark:bg-amber-500/15 dark:text-amber-100">{t("metaAds.notActiveStatus")}</span>
      </div>

      <div className="grid gap-3 rounded-2xl border border-indigo-100 bg-indigo-50 p-4 text-sm text-indigo-950 dark:border-indigo-400/20 dark:bg-indigo-500/10 dark:text-indigo-100 sm:grid-cols-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.15em] opacity-70">{t("metaAds.statusLabel")}</p>
          <p className="mt-1 font-black">{t("metaAds.notActiveStatus")}</p>
        </div>
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.15em] opacity-70">{t("metaAds.currentSourceLabel")}</p>
          <p className="mt-1 font-black">{t("metaAds.currentSourceValue")}</p>
        </div>
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.15em] opacity-70">{t("metaAds.futureLabel")}</p>
          <p className="mt-1 font-black">{t("metaAds.futureValue")}</p>
        </div>
      </div>

      <div className="grid gap-3 rounded-2xl border border-emerald-100 bg-emerald-50 p-4 text-sm text-emerald-950 dark:border-emerald-400/20 dark:bg-emerald-500/10 dark:text-emerald-100">
        <p className="font-bold">{t("metaAds.manualCsvProtection")}</p>
        <p>{t("metaAds.deliveryMetricsOnly")}</p>
        <p>{t("metaAds.mockOAuthPrepared")}</p>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <button
          aria-describedby="meta-ads-coming-soon-help"
          className="min-h-11 w-full cursor-not-allowed rounded-xl bg-slate-200 px-4 py-3 text-sm font-black text-slate-500 dark:bg-slate-800 dark:text-slate-300 sm:w-auto"
          disabled
          type="button"
        >
          {t("metaAds.connectComingSoon")}
        </button>
        <p id="meta-ads-coming-soon-help" className="text-sm text-slate-600 dark:text-slate-300">{t("metaAds.comingSoonHelp")}</p>
      </div>

      {featureGates.metaAdsSyncPreviewEnabled ? (
        <div className="grid gap-3 rounded-2xl border border-dashed border-slate-300 p-4 dark:border-slate-700" data-meta-ads-demo-preview="future-non-writing-preview-only">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">{t("metaAds.demoPreviewEyebrow")}</p>
            <h3 className="mt-1 font-black">{t("metaAds.demoPreviewTitle")}</h3>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{t("metaAds.demoPreviewDescription")}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {previewStatuses.map((status) => (
              <span key={status} className="rounded-full border border-slate-200 px-3 py-1 text-xs font-bold text-slate-700 dark:border-slate-700 dark:text-slate-200">
                {t(`metaAds.previewStatuses.${status}`)}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {!compact ? (
        <ol className="grid gap-2 text-sm text-slate-600 dark:text-slate-300" data-meta-ads-admin-review-flow="future-docs-only-no-steps-1-5-6-implemented">
          <li>1. {t("metaAds.reviewFlowStep1")}</li>
          <li>2. {t("metaAds.reviewFlowStep2")}</li>
          <li>3. {t("metaAds.reviewFlowStep3")}</li>
          <li>4. {t("metaAds.reviewFlowStep4")}</li>
          <li>5. {t("metaAds.reviewFlowStep5")}</li>
          <li>6. {t("metaAds.reviewFlowStep6")}</li>
        </ol>
      ) : null}
    </section>
  );
}
