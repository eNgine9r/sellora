"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity } from "lucide-react";
import { useEffect, useState } from "react";
import { Button, Card, LoadingSkeleton, StatusBadge } from "@/components/ui/primitives";
import { useI18n } from "@/i18n/provider";
import { platformAdminApi, type UsageDays } from "@/services/platform-admin";
import { accessDenied, PlatformProblem } from "./platform-feedback";

const periodOptions = [7, 30] as const;
const summaryMetrics = ["active_workspaces", "activated_workspaces", "first_products", "first_orders", "orders_created", "integration_days"] as const;
const workspaceMetrics = ["active_workspace_days", "first_products", "first_orders", "orders_created", "integration_days"] as const;

export function PlatformActivity({ operatorId, workspaceId, recheckAccess }: {
  operatorId: string;
  workspaceId?: string;
  recheckAccess: () => void;
}) {
  const { t, locale } = useI18n();
  const [days, setDays] = useState<UsageDays>(7);
  const activity = useQuery({
    queryKey: ["platform-admin", operatorId, "activity", workspaceId ?? "summary", days],
    queryFn: ({ signal }) => platformAdminApi.activity(days, workspaceId, signal),
    gcTime: 0,
    retry: false,
  });
  const denied = accessDenied(activity.error);
  useEffect(() => { if (denied) recheckAccess(); }, [denied, recheckAccess]);

  const report = activity.error ? undefined : activity.data;
  const number = new Intl.NumberFormat(locale);
  const date = new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeZone: "UTC" });
  const metrics = workspaceId ? workspaceMetrics : summaryMetrics;
  const totals = report?.totals;
  const title = t("platformActivity.title");

  return (
    <Card className="grid min-w-0 gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 font-black">
          <Activity className="size-5 text-violet-400" aria-hidden="true" />{title}
        </h2>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label={t("platformActivity.period")}>
          {periodOptions.map((option) => (
            <Button key={option} variant={days === option ? "brand" : "secondary"} size="sm" aria-pressed={days === option} onClick={() => setDays(option)}>
              {t(`platformActivity.days${option}`)}
            </Button>
          ))}
        </div>
      </div>
      {activity.isPending ? <LoadingSkeleton title={t("platformActivity.loading")} rows={1} /> : null}
      {activity.error ? <PlatformProblem message={denied ? "forbidden" : "error"} retry={denied ? undefined : () => void activity.refetch()} /> : null}
      {report ? (
        <>
          <p className="text-xs text-text-secondary">{t("platformActivity.range", {
            from: date.format(new Date(report.from_day)),
            to: date.format(new Date(report.to_day)),
          })}</p>
          {report.coverage !== "complete" ? (
            <div className="flex flex-wrap items-center gap-2" role="status">
              <StatusBadge tone={report.coverage === "partial" ? "warning" : "neutral"}>{t(`platformActivity.${report.coverage}`)}</StatusBadge>
              <p className="text-xs text-text-secondary">{t(`platformActivity.${report.coverage}Description`)}</p>
            </div>
          ) : null}
          {totals ? (
            <dl className={`grid grid-cols-2 gap-2 ${workspaceId ? "" : "sm:grid-cols-3 xl:grid-cols-6"}`}>
              {metrics.map((metric) => (
                <div key={metric} className="min-w-0 rounded-2xl border border-border-subtle bg-surface-2 p-3">
                  <dt className="text-xs font-semibold text-text-secondary">{t(`platformActivity.metrics.${metric}`)}</dt>
                  <dd className="mt-1 text-xl font-black tabular-nums" data-testid={`activity-${metric}`}>{number.format(totals[metric])}</dd>
                </div>
              ))}
            </dl>
          ) : null}
        </>
      ) : null}
    </Card>
  );
}
