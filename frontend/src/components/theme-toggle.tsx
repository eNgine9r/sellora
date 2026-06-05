"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/providers/theme-provider";
import { useI18n } from "@/i18n/provider";

export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const { mode, resolvedTheme, setMode } = useTheme();
  const { t } = useI18n();
  const nextMode = resolvedTheme === "dark" ? "light" : "dark";
  const Icon = resolvedTheme === "dark" ? Sun : Moon;
  return (
    <button
      className={`inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-3 text-sm font-bold text-slate-700 shadow-sm transition hover:border-violet-200 hover:text-violet-700 dark:border-white/10 dark:bg-white/10 dark:text-slate-100 dark:hover:bg-white/15 ${compact ? "w-11 px-0" : ""}`}
      type="button"
      onClick={() => setMode(nextMode)}
      aria-label={`${t("theme.label")}: ${t(`theme.${mode}`)}, ${t("theme.switchTo")} ${t(`theme.${nextMode}`)}.`}
      title={`${t("theme.label")}: ${t(`theme.${mode}`)} · ${t("theme.switchTo")} ${t(`theme.${nextMode}`)}`}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {compact ? null : <span className="hidden sm:inline">{resolvedTheme === "dark" ? t("theme.lightShort") : t("theme.darkShort")}</span>}
    </button>
  );
}
