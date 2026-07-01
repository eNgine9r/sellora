"use client";

import { Globe2 } from "lucide-react";
import { Locale, locales } from "@/i18n/config";
import { useI18n } from "@/i18n/provider";

export function LanguageSwitcher({ compact = false }: { compact?: boolean }) {
  const { locale, setLocale, t } = useI18n();
  return (
    <label className={`inline-flex min-h-11 shrink-0 items-center gap-2 rounded-2xl border border-slate-200 bg-white px-3 text-sm font-bold text-slate-700 shadow-sm dark:border-white/10 dark:bg-white/10 dark:text-slate-100 ${compact ? "px-2" : ""}`}>
      <Globe2 className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span className="sr-only">{t("language.label")}</span>
      <select
        className="h-8 w-[4.6rem] min-w-0 rounded-xl border-0 bg-transparent px-1 text-xs font-black uppercase outline-none dark:bg-transparent dark:text-white"
        value={locale}
        onChange={(event) => setLocale(event.target.value as Locale)}
        aria-label={t("language.label")}
      >
        {locales.map((item) => <option key={item} value={item}>{t(`language.short${item === "uk" ? "Uk" : "En"}`)}</option>)}
      </select>
    </label>
  );
}
