export type StatusTone = "success" | "warning" | "danger" | "info" | "neutral" | "violet";

export const statusBadgeBase = "sellora-status-badge inline-flex max-w-full items-center rounded-full border px-3 py-1 text-xs font-bold leading-none";

export const statusToneClasses: Record<StatusTone, string> = {
  success: "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-400/30 dark:bg-emerald-400/15 dark:text-emerald-100",
  warning: "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-400/30 dark:bg-amber-400/15 dark:text-amber-100",
  danger: "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-400/30 dark:bg-rose-400/15 dark:text-rose-100",
  info: "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-400/30 dark:bg-blue-400/15 dark:text-blue-100",
  neutral: "border-slate-200 bg-slate-100 text-slate-700 dark:border-slate-400/30 dark:bg-slate-400/15 dark:text-slate-100",
  violet: "border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-400/30 dark:bg-violet-400/15 dark:text-violet-100",
};

export function statusBadgeClass(tone: StatusTone) {
  return `${statusBadgeBase} ${statusToneClasses[tone]}`;
}
