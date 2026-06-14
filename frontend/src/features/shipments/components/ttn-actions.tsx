"use client";

import { useState } from "react";
import { useI18n } from "@/i18n/provider";

export function CopyTtnButton({ trackingNumber, variant = "secondary" }: { trackingNumber?: string | null; variant?: "primary" | "secondary" }) {
  const { t } = useI18n();
  const [message, setMessage] = useState<string | null>(null);
  const canCopy = Boolean(trackingNumber);
  const className =
    variant === "primary"
      ? "min-h-11 rounded-xl bg-blue-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-60"
      : "min-h-11 rounded-xl border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700 disabled:opacity-60 dark:border-white/10 dark:text-slate-100";

  async function copyTrackingNumber() {
    if (!trackingNumber) return;
    try {
      await navigator.clipboard.writeText(trackingNumber);
      setMessage(t("shipments.ttnCopied"));
    } catch {
      setMessage(t("shipments.ttnCopyFailed"));
    }
  }

  return (
    <div className="grid gap-1">
      <button className={className} type="button" disabled={!canCopy} onClick={() => void copyTrackingNumber()}>
        {t("shipments.copyTtn")}
      </button>
      {message ? <p className="text-xs font-semibold text-blue-700 dark:text-blue-200">{message}</p> : null}
    </div>
  );
}

export function TtnDocumentLimitation() {
  const { t } = useI18n();
  return (
    <p className="rounded-xl bg-amber-50 p-3 text-xs font-semibold text-amber-800 dark:bg-amber-500/15 dark:text-amber-100">
      {t("shipments.ttnPrintUnavailable")} {t("shipments.ttnPrintWorkaround")}
    </p>
  );
}
