"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { ChevronRight, CircleCheck, Info } from "lucide-react";

type Tone = "violet" | "amber" | "rose" | "emerald";
export type DashboardAction = {
  title: string;
  description: string;
  href: string;
  action: string;
  tone: Tone;
};

const actionTones: Record<Tone, string> = {
  violet: "bg-violet-500",
  amber: "bg-amber-500",
  rose: "bg-rose-500",
  emerald: "bg-emerald-500",
};

export function DashboardMetricCard({
  label,
  value,
  helper,
  trend,
  unavailable = false,
  emphasized = false,
  explanation,
}: {
  label: string;
  value: ReactNode;
  helper: string;
  trend?: string;
  unavailable?: boolean;
  emphasized?: boolean;
  explanation?: string;
}) {
  return (
    <article className={"group relative flex min-w-0 flex-col justify-between overflow-hidden rounded-2xl border border-border-subtle bg-surface-1 p-4 transition-colors duration-200 hover:border-border-strong sm:p-5 " + (emphasized ? "dark:bg-[linear-gradient(130deg,var(--surface-2),var(--surface-1))]" : "")}>
      {emphasized ? <span aria-hidden="true" className="pointer-events-none absolute inset-x-5 top-0 h-px bg-gradient-to-r from-transparent via-violet-400/65 to-transparent" /> : null}
      <div className="flex min-w-0 items-center justify-between gap-2">
        <p className="min-w-0 flex-1 break-words text-[11px] font-semibold leading-4 tracking-wide text-text-secondary sm:text-xs">{label}</p>
        {explanation ? <span title={explanation} aria-label={explanation} tabIndex={0} className="flex h-5 w-5 shrink-0 items-center justify-center rounded text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"><Info aria-hidden="true" className="h-3.5 w-3.5" /></span> : null}
      </div>
      <div className={"mt-3 min-w-0 break-words text-[clamp(1.125rem,4.6vw,2rem)] font-semibold leading-tight tracking-tight tabular-nums " + (unavailable ? "text-text-secondary" : "text-text-primary")}>{value}</div>
      <div className="mt-4 flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
        {trend ? <span className="shrink-0 rounded-md border border-border-subtle bg-surface-2 px-1.5 py-0.5 text-[11px] font-semibold tabular-nums text-text-secondary">{trend}</span> : null}
        <p className="min-w-0 text-xs leading-4 text-text-muted" title={helper}>{helper}</p>
      </div>
    </article>
  );
}

export function DashboardActionList({
  items,
  emptyText,
}: {
  items: DashboardAction[];
  emptyText: string;
}) {
  if (!items.length) {
    return <div className="flex items-start gap-2 rounded-xl border border-border-subtle bg-surface-2 p-3 text-sm text-text-secondary"><CircleCheck aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-success-foreground" />{emptyText}</div>;
  }
  return (
    <ul className="grid gap-1">
      {items.slice(0, 4).map((item) => (
        <li key={item.title}><Link
          href={item.href}
          aria-label={item.title + ". " + item.action}
          className="group flex min-w-0 items-start gap-3 rounded-xl px-2 py-2.5 transition-colors duration-150 hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
        >
          <span aria-hidden="true" className={"mt-1.5 h-2 w-2 shrink-0 rounded-full " + actionTones[item.tone]} />
          <div className="min-w-0 flex-1">
            <p className="break-words text-sm font-semibold leading-snug text-text-primary">{item.title}</p>
            <p className="mt-0.5 line-clamp-2 text-xs leading-5 text-text-secondary">{item.description}</p>
          </div>
          <ChevronRight aria-hidden="true" className="mt-1 h-4 w-4 shrink-0 text-text-muted transition-transform group-hover:translate-x-0.5" />
        </Link></li>
      ))}
    </ul>
  );
}

export function DashboardFunnel({
  stages,
}: {
  stages: { label: string; value: number; helper: string; color: string }[];
}) {
  const maxValue = Math.max(1, ...stages.map((stage) => stage.value));
  return (
    <div className="grid min-w-0 gap-2 sm:grid-cols-3">
      {stages.map((stage, index) => (
        <div key={stage.label} className="min-w-0 rounded-xl border border-border-subtle bg-surface-2 p-3.5">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate text-xs font-medium text-text-secondary">{stage.label}</span>
            <span aria-hidden="true" className="text-xs font-medium text-text-muted">{String(index + 1).padStart(2, "0")}</span>
          </div>
          <p className="mt-2 text-2xl font-semibold leading-none tracking-tight text-text-primary tabular-nums">{stage.value.toLocaleString("uk-UA")}</p>
          <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-surface-3">
            <div className={"h-full rounded-full transition-[width] duration-300 motion-reduce:transition-none " + stage.color} style={{ width: (stage.value / maxValue) * 100 + "%" }} />
          </div>
          <p className="mt-2 min-h-8 text-xs leading-4 text-text-muted">{stage.helper}</p>
        </div>
      ))}
    </div>
  );
}
