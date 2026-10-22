"use client";

import { useEffect, useState } from "react";
import { BrandIcon } from "@/components/brand";
import { useI18n } from "@/i18n/provider";

type LoadingStage = "initial" | "slow" | "delayed";

export function GlobalAppLoader() {
  const { t } = useI18n();
  const [stage, setStage] = useState<LoadingStage>("initial");

  useEffect(() => {
    const slowTimer = window.setTimeout(() => setStage("slow"), 5000);
    const delayedTimer = window.setTimeout(() => setStage("delayed"), 12000);

    return () => {
      window.clearTimeout(slowTimer);
      window.clearTimeout(delayedTimer);
    };
  }, []);

  const message =
    stage === "delayed"
      ? t("common.loadingDelayed")
      : stage === "slow"
        ? t("common.loadingSlow")
        : t("common.loadingWorkspace");

  return (
    <div
      className="flex min-h-screen min-h-[100dvh] w-full flex-col items-center justify-center bg-canvas px-6 py-12 text-center text-text-primary"
      data-app-orbit-loader
      data-loading-stage={stage}
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      <div className="sellora-orbit relative grid h-16 w-16 place-items-center md:h-20 md:w-20">
        <span className="sellora-orbit-track" aria-hidden="true" />
        <span className="sellora-orbit-spinner" aria-hidden="true" />
        <span className="relative z-10" aria-hidden="true">
          <BrandIcon priority unoptimized className="h-7 w-7 md:h-9 md:w-9" />
        </span>
      </div>
      <span className="mt-5 text-lg font-bold tracking-tight text-text-primary md:text-xl">Sellora</span>
      <p className="mt-2 max-w-xs text-sm leading-6 text-text-secondary md:text-base">{message}</p>
      {stage === "delayed" ? (
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="mt-5 min-h-11 rounded-xl border border-border-subtle bg-surface-1 px-5 py-2 text-sm font-semibold text-text-primary transition-colors hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
        >
          {t("common.retry")}
        </button>
      ) : null}
    </div>
  );
}
