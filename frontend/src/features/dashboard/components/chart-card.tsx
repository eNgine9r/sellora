import type { ReactNode } from "react";

export function ChartCard({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <section className="min-w-0 overflow-hidden rounded-xl border border-border-subtle bg-surface-1 p-3 sm:p-4">
      <header className="mb-3 min-w-0">
        <h2 className="break-words text-sm font-semibold tracking-tight text-text-primary sm:text-base">{title}</h2>
        {subtitle ? <p className="mt-0.5 line-clamp-1 text-xs leading-4 text-text-secondary" title={subtitle}>{subtitle}</p> : null}
      </header>
      {children}
    </section>
  );
}
