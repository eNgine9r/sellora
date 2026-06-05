"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "@/providers/theme-provider";

const labels = {
  system: "System theme",
  light: "Light theme",
  dark: "Dark theme",
} as const;

export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const { mode, resolvedTheme, cycleMode } = useTheme();
  const Icon = mode === "system" ? Monitor : mode === "dark" ? Moon : Sun;
  return (
    <button
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-3 text-sm font-bold text-slate-700 shadow-sm transition hover:border-violet-200 hover:text-violet-700 dark:border-white/10 dark:bg-white/10 dark:text-slate-100 dark:hover:bg-white/15 ${compact ? "w-11 px-0" : ""}`}
      type="button"
      onClick={cycleMode}
      aria-label={`Theme: ${labels[mode]}, resolved ${resolvedTheme}. Click to switch theme.`}
      title={`Theme: ${labels[mode]}`}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {compact ? null : <span className="hidden sm:inline">{mode === "system" ? "System" : mode === "dark" ? "Dark" : "Light"}</span>}
    </button>
  );
}
