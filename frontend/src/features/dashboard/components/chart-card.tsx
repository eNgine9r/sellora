import type { ReactNode } from "react";

export function ChartCard({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <section className="min-w-0 overflow-hidden rounded-2xl border border-border-subtle bg-surface-1 p-4 sm:p-5">
      <header className="mb-4 min-w-0">
        <h2 className="break-words text-base font-semibold tracking-tight text-text-primary sm:text-lg">{title}</h2>
        {subtitle ? <p className="mt-1 break-words text-xs leading-5 text-text-secondary">{subtitle}</p> : null}
      </header>
      {children}
    </section>
  );
}
