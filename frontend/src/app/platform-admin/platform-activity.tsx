"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, CalendarDays } from "lucide-react";
import { useEffect, useState } from "react";
import { Button, Card, LoadingSkeleton, StatusBadge } from "@/components/ui/primitives";
import { useI18n } from "@/i18n/provider";
import { platformAdminApi, type ProductUsageDay, type UsageDays } from "@/services/platform-admin";
import { accessDenied, PlatformProblem } from "./platform-feedback";

const periodOptions = [7, 30] as const;
const summaryMetrics = ["active_workspaces", "activated_workspaces", "first_products", "first_orders", "orders_created", "integration_days"] as const;
const workspaceMetrics = ["active_workspace_days", "first_products", "first_orders", "orders_created", "integration_days"] as const;

function DailyOrders({ daily }: { daily: ProductUsageDay[] }) {
  const { t, locale } = useI18n();
  const date = new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", timeZone: "UTC" });
  const number = new Intl.NumberFormat(locale);
  const formatDay = (day: string) => date.format(new Date(day));
  const max = Math.max(1, ...daily.map((point) => point.orders_created));

  return (
    <figure className="min-w-0 rounded-2xl border border-border-subtle bg-canvas/60 p-4 sm:p-5">
      <figcaption className="text-sm font-semibold">{t("platformActivity.dailyOrders")}</figcaption>
      <p className="mt-1 text-xs leading-5 text-text-secondary">{t("platformActivity.dailyOrdersDescription")}</p>
      <div aria-hidden="true" className="mt-4 grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2">
        <div className="flex flex-col justify-between text-[11px] tabular-nums text-text-secondary">
          <span>{number.format(max)}</span>
          <span>0</span>
        </div>
        <div className="relative grid h-28 items-end gap-0.5 border-b border-t border-border-subtle sm:gap-1.5" style={{ gridTemplateColumns: `repeat(${daily.length}, minmax(0, 1fr))` }}>
          {daily.map((point) => (
            <div
              key={point.day}
              title={t("platformActivity.dailyValue", { day: formatDay(point.day), count: number.format(point.orders_created) })}
              className={`mx-auto w-full max-w-10 rounded-t-sm ${point.dropped_operations ? "bg-amber-400/80" : "bg-gradient-to-t from-violet-600 to-violet-300"}`}
              style={{ height: `max(2px, ${point.orders_created / max * 100}%)` }}
            />
          ))}
        </div>
        <div className="col-start-2 flex flex-wrap justify-between gap-x-2 text-[11px] text-text-secondary">
          <span>{formatDay(daily[0].day)}</span>
          {daily.length > 1 ? <span>{formatDay(daily[daily.length - 1].day)}</span> : null}
        </div>
      </div>
      <details className="mt-4 border-t border-border-subtle pt-3">
        <summary className="w-fit cursor-pointer rounded text-xs font-semibold text-violet-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring">{t("platformActivity.dailyTable")}</summary>
        <table className="mt-3 w-full text-left text-xs" aria-label={t("platformActivity.dailyOrders")}>
          <thead className="text-text-secondary">
            <tr>
              <th className="py-1.5" scope="col">{t("platformActivity.day")}</th>
              <th className="py-1.5 text-right" scope="col">{t("platformActivity.metrics.orders_created")}</th>
            </tr>
          </thead>
          <tbody>
            {daily.map((point) => (
              <tr className="border-t border-border-subtle" key={point.day}>
                <th scope="row" className="py-1.5 font-normal">
                  <time dateTime={point.day}>{formatDay(point.day)}</time>
                  {point.dropped_operations ? <span className="ml-2 text-amber-300">{t("platformActivity.partial")}</span> : null}
                </th>
                <td className="py-1.5 text-right tabular-nums">{number.format(point.orders_created)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}

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
  const Heading = workspaceId ? "h3" : "h2";

  return (
    <Card className="grid min-w-0 gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Heading className="flex items-center gap-2.5 text-lg font-bold tracking-tight sm:text-xl">
          <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-violet-500/15 text-violet-300">
            <Activity className="size-4" aria-hidden="true" />
          </span>
          {t("platformActivity.title")}
        </Heading>
        <div className="flex gap-1 rounded-xl border border-border-subtle bg-canvas p-1" role="group" aria-label={t("platformActivity.period")}>
          {periodOptions.map((option) => (
            <Button key={option} variant={days === option ? "secondary" : "ghost"} size="sm" aria-pressed={days === option} onClick={() => setDays(option)}>
              {t(`platformActivity.days${option}`)}
            </Button>
          ))}
        </div>
      </div>
      {activity.isPending ? <LoadingSkeleton title={t("platformActivity.loading")} rows={1} /> : null}
      {activity.error ? <PlatformProblem message={denied ? "forbidden" : "error"} retry={denied ? undefined : () => void activity.refetch()} /> : null}
      {report ? (
        <>
          <p className="flex items-center gap-2 text-xs text-text-secondary">
            <CalendarDays className="size-3.5" aria-hidden="true" />
            {t("platformActivity.range", {
              from: date.format(new Date(report.from_day)),
              to: date.format(new Date(report.to_day)),
            })}
          </p>
          {report.coverage !== "complete" ? (
            <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border-subtle bg-surface-2 px-3 py-2.5" role="status">
              <StatusBadge tone={report.coverage === "partial" ? "warning" : "neutral"}>{t(`platformActivity.${report.coverage}`)}</StatusBadge>
              <p className="text-xs leading-5 text-text-secondary">{t(`platformActivity.${report.coverage}Description`)}</p>
            </div>
          ) : null}
          {totals ? (
            <dl className={`grid grid-cols-2 gap-2 ${workspaceId ? "" : "sm:grid-cols-3 lg:grid-cols-6"}`}>
              {metrics.map((metric) => (
                <div key={metric} className="flex min-w-0 flex-col rounded-xl border border-border-subtle bg-surface-2 p-3">
                  <dt className="order-last mt-1 text-xs font-medium leading-5 text-text-secondary">{t(`platformActivity.metrics.${metric}`)}</dt>
                  <dd className="text-2xl font-bold tracking-tight tabular-nums" data-testid={`activity-${metric}`}>{number.format(totals[metric])}</dd>
                </div>
              ))}
            </dl>
          ) : null}
          {report.daily?.length ? <DailyOrders daily={report.daily} /> : null}
        </>
      ) : null}
    </Card>
  );
}
