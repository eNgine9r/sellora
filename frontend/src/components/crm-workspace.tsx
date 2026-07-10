"use client";

import { ReactNode } from "react";
import { Card, PageHeader, StatusBadge, Button } from "@/components/ui/primitives";
import { Drawer } from "@/components/ui/overlay";
import { cn } from "@/services/utils";

type MetricTone = "neutral" | "success" | "warning" | "danger" | "info";

export function WorkspacePage({ children, className }: { children: ReactNode; className?: string }) {
  return <main className={cn("min-w-0 overflow-x-hidden px-4 py-4 text-text-primary sm:px-6 sm:py-6", className)}><div className="grid min-w-0 w-full gap-5 lg:gap-6">{children}</div></main>;
}

export function WorkspaceHeader({ title, description, eyebrow, actions }: { title: string; description?: string; eyebrow?: string; actions?: ReactNode }) {
  return <div className="grid gap-2">{eyebrow ? <p className="text-xs font-black uppercase tracking-[0.18em] text-primary">{eyebrow}</p> : null}<PageHeader title={title} description={description} actions={actions} /></div>;
}

export function MetricCard({ label, value, helper, trend, tone = "neutral", isUnavailable = false }: { label: string; value: ReactNode; helper?: ReactNode; trend?: string; tone?: MetricTone; isUnavailable?: boolean }) {
  const badgeVariant = tone === "success" ? "success" : tone === "warning" ? "warning" : tone === "danger" ? "danger" : tone === "info" ? "info" : "neutral";
  return <Card className="min-w-0 p-4">
    <div className="flex min-w-0 items-start justify-between gap-3">
      <div className="min-w-0">
        <p className="text-xs font-black uppercase tracking-[0.16em] text-text-muted">{label}</p>
        <div className={cn("mt-2 truncate text-2xl font-black text-text-primary", isUnavailable && "text-text-muted")}>{value}</div>
      </div>
      {trend ? <StatusBadge tone={badgeVariant}>{trend}</StatusBadge> : null}
    </div>
    {helper ? <p className="mt-2 text-sm font-medium text-text-secondary">{helper}</p> : null}
  </Card>;
}

export function CompactSummary({ items }: { items: { label: string; value: ReactNode; helper?: string; active?: boolean; onClick?: () => void; unavailable?: boolean }[] }) {
  return <section className="grid min-w-0 gap-3 [grid-template-columns:repeat(auto-fit,minmax(min(180px,100%),1fr))]">{items.map((item) => {
    const content = <><p className="text-xs font-black uppercase tracking-[0.14em] text-text-muted">{item.label}</p><p className={cn("mt-2 text-2xl font-black text-text-primary", item.unavailable && "text-text-muted")}>{item.unavailable ? "—" : item.value}</p>{item.helper ? <p className="mt-1 text-sm text-text-secondary">{item.helper}</p> : null}</>;
    if (item.onClick) return <button key={item.label} type="button" onClick={item.onClick} className={cn("rounded-2xl border border-border-subtle bg-surface-1 p-4 text-left shadow-sm transition hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring", item.active && "border-primary bg-surface-selected")}>{content}</button>;
    return <Card key={item.label} className={cn("p-4", item.active && "border-primary bg-surface-selected")}>{content}</Card>;
  })}</section>;
}

export function ToolbarShell({ children }: { children: ReactNode }) {
  return <Card className="flex min-w-0 flex-col gap-3 p-3 md:flex-row md:flex-wrap md:items-center">{children}</Card>;
}

export function EntityDrawer({ title, description, open, onClose, children, footer }: { title: string; description?: string; open: boolean; onClose: () => void; children: ReactNode; footer?: ReactNode }) {
  return <Drawer open={open} onClose={onClose} title={title} description={description} footer={footer}>{children}</Drawer>;
}

export function FieldGrid({ children }: { children: ReactNode }) {
  return <dl className="grid min-w-0 gap-3 sm:grid-cols-2">{children}</dl>;
}

export function FieldItem({ label, value }: { label: string; value: ReactNode }) {
  return <div className="min-w-0 rounded-2xl border border-border-subtle bg-surface-2 p-3"><dt className="text-xs font-black uppercase tracking-[0.14em] text-text-muted">{label}</dt><dd className="mt-1 break-words text-sm font-semibold text-text-primary">{value || "—"}</dd></div>;
}

export function DrawerTabs({ tabs, active, onChange }: { tabs: { id: string; label: string }[]; active: string; onChange: (id: string) => void }) {
  return <div className="sellora-scrollbar flex min-w-0 gap-2 overflow-x-auto rounded-2xl border border-border-subtle bg-surface-2 p-1" role="tablist">{tabs.map((tab) => <button key={tab.id} type="button" role="tab" aria-selected={active === tab.id} onClick={() => onChange(tab.id)} className={cn("min-h-10 shrink-0 rounded-xl px-3 text-sm font-bold text-text-secondary transition hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring", active === tab.id && "bg-surface-selected text-primary")}>{tab.label}</button>)}</div>;
}

export { Button };
