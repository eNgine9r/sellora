"use client";

import { useI18n } from "@/i18n/provider";

export type DashboardActivity = { label: string; date: string };

export function ActivityFeed({ events = [] }: { events?: DashboardActivity[] }) {
  const { t } = useI18n();
  return (
    <section className="min-w-0 rounded-xl border border-border-subtle bg-surface-1 p-3 sm:p-4">
      <h2 className="text-sm font-semibold tracking-tight text-text-primary sm:text-base">{t("dashboard.activity")}</h2>
      <ol className="mt-3 grid min-w-0 gap-2">
        {events.length ? events.map((event) => (
          <li key={event.label + event.date} className="flex min-w-0 gap-3">
            <span aria-hidden="true" className="relative mt-1.5 h-2 w-2 shrink-0 rounded-full bg-violet-500" />
            <div className="min-w-0">
              <p className="break-words text-xs font-medium leading-4 text-text-primary">{event.label}</p>
              <time dateTime={event.date} className="mt-0.5 block text-[11px] text-text-muted">{new Date(event.date).toLocaleDateString("uk-UA")}</time>
            </div>
          </li>
        )) : <li className="rounded-xl bg-surface-2 p-3 text-sm text-text-secondary">{t("dashboard.emptyStates.noActivity")}</li>}
      </ol>
    </section>
  );
}
