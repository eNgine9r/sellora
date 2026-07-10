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
      className={`inline-flex shrink-0 items-center justify-center gap-2 rounded-2xl border border-border-subtle bg-surface-2 px-3 text-sm font-bold text-text-primary shadow-sm transition hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring ${compact ? "h-10 min-h-10 w-10 px-0" : "min-h-11"}`}
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
