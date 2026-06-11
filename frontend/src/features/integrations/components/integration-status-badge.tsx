import { IntegrationStatus } from "@/types/integrations";
import { useI18n } from "@/i18n/provider";

const COLORS: Record<IntegrationStatus, string> = {
  CONNECTED: "border border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-400/30 dark:bg-emerald-500/15 dark:text-emerald-100",
  DISCONNECTED: "border border-slate-200 bg-slate-100 text-slate-600 dark:border-white/10 dark:bg-white/10 dark:text-slate-100",
  ERROR: "border border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-400/40 dark:bg-rose-500/20 dark:text-rose-100",
};
export function IntegrationStatusBadge({ status }: { status: IntegrationStatus }) {
  const { t } = useI18n();
  return <span className={`rounded-full px-3 py-1 text-xs font-bold ${COLORS[status]}`}>{t(`novaPoshta.status.${status}`)}</span>;
}
