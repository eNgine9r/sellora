"use client";

import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";
import { AlertCircle, Check, ChevronLeft, ChevronRight, Inbox, Loader2 } from "lucide-react";
import { twMerge } from "tailwind-merge";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "brand";
type Size = "sm" | "md" | "lg";

const buttonVariants: Record<Variant, string> = {
  primary: "bg-primary text-primary-foreground shadow-[var(--shadow-control)] hover:bg-primary-hover active:bg-primary-active",
  secondary: "border border-border-subtle bg-surface-2 text-text-primary hover:border-border-strong hover:bg-surface-hover active:bg-surface-3",
  ghost: "text-text-secondary hover:bg-surface-2 hover:text-text-primary active:bg-surface-3",
  danger: "bg-danger text-primary-foreground hover:brightness-110 active:brightness-95",
  brand: "bg-brand-gradient text-primary-foreground shadow-[var(--shadow-brand)] hover:brightness-110 active:brightness-95",
};

const buttonSizes: Record<Size, string> = {
  sm: "min-h-10 rounded-xl px-3 text-xs",
  md: "min-h-11 rounded-2xl px-4 text-sm",
  lg: "min-h-12 rounded-2xl px-5 text-sm",
};

export function Button({ className, variant = "primary", size = "md", loading = false, disabled, children, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size; loading?: boolean }) {
  return (
    <button
      className={twMerge(
        "inline-flex min-w-0 items-center justify-center gap-2 whitespace-nowrap font-black transition duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-canvas disabled:cursor-not-allowed disabled:opacity-55",
        buttonVariants[variant],
        buttonSizes[size],
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
      {children}
    </button>
  );
}

export function IconButton({ className, variant = "secondary", loading = false, disabled, children, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; loading?: boolean }) {
  return <Button className={twMerge("h-11 w-11 min-h-11 min-w-11 p-0", className)} variant={variant} disabled={disabled} loading={loading} {...props}>{children}</Button>;
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <section className={twMerge("rounded-[var(--radius-card)] border border-border-subtle bg-surface-1 p-4 shadow-[var(--shadow-card)] sm:p-5", className)}>{children}</section>;
}

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return <div className="grid min-w-0 gap-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end"><div className="min-w-0"><h1 className="break-words text-2xl font-black tracking-[-0.03em] text-text-primary md:text-3xl">{title}</h1>{description ? <p className="mt-2 max-w-3xl text-sm leading-6 text-text-secondary">{description}</p> : null}</div>{actions ? <div className="grid min-w-0 gap-2 sm:flex sm:shrink-0 sm:flex-wrap sm:justify-end [&>*]:w-full sm:[&>*]:w-auto">{actions}</div> : null}</div>;
}

export function StatusBadge({ children, tone = "info" }: { children: ReactNode; tone?: "success" | "warning" | "danger" | "info" | "neutral" }) {
  const tones = { success: "border-success/30 bg-[var(--success-surface)] text-[var(--success-foreground)]", warning: "border-warning/30 bg-[var(--warning-surface)] text-[var(--warning-foreground)]", danger: "border-danger/30 bg-[var(--danger-surface)] text-[var(--danger-foreground)]", info: "border-info/30 bg-[var(--info-surface)] text-[var(--info-foreground)]", neutral: "border-border-subtle bg-surface-2 text-text-secondary" };
  return <span className={twMerge("sellora-status-badge inline-flex min-h-7 items-center rounded-full border px-2.5 text-xs font-black", tones[tone])}>{children}</span>;
}

export function FormField({ label, hint, error, children }: { label: string; hint?: string; error?: string | null; children: ReactNode }) {
  return <label className="grid min-w-0 gap-2 text-sm font-bold text-text-primary"><span>{label}</span>{children}{hint && !error ? <span className="text-xs font-semibold text-text-muted">{hint}</span> : null}{error ? <span className="inline-flex items-center gap-1 text-xs font-bold text-danger"><AlertCircle className="h-3.5 w-3.5" />{error}</span> : null}</label>;
}

const controlClass = "h-11 min-h-11 w-full min-w-0 rounded-2xl border border-input-border bg-input-background px-3 text-sm font-semibold text-text-primary outline-none transition placeholder:text-text-muted hover:border-border-strong focus:border-focus-ring focus:ring-2 focus:ring-focus-ring/30 disabled:cursor-not-allowed disabled:opacity-55 aria-[invalid=true]:border-danger aria-[invalid=true]:focus:ring-danger/25";
export function Input(props: InputHTMLAttributes<HTMLInputElement>) { return <input {...props} className={twMerge(controlClass, props.className)} />; }
export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) { return <select {...props} className={twMerge(controlClass, props.className)} />; }
export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) { return <textarea {...props} className={twMerge(controlClass, "min-h-28 py-3", props.className)} />; }
export function Checkbox(props: InputHTMLAttributes<HTMLInputElement>) { return <input type="checkbox" {...props} className={twMerge("h-4 w-4 rounded border-border-strong bg-surface-2 text-primary focus:ring-2 focus:ring-focus-ring/40", props.className)} />; }

export function FilterBar({ children, className }: { children: ReactNode; className?: string }) { return <div className={twMerge("flex min-w-0 flex-col gap-3 rounded-[var(--radius-card)] border border-border-subtle bg-surface-1 p-3 md:flex-row md:flex-wrap md:items-center [&>*]:min-w-0", className)}>{children}</div>; }
export function Tabs({ tabs, active, onChange }: { tabs: { id: string; label: string }[]; active: string; onChange: (id: string) => void }) { return <div className="sellora-scrollbar flex max-w-full overflow-x-auto rounded-2xl border border-border-subtle bg-surface-1 p-1">{tabs.map((tab) => <button key={tab.id} className={twMerge("min-h-10 shrink-0 rounded-xl px-3 text-sm font-black text-text-secondary transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring", active === tab.id && "bg-surface-3 text-text-primary")} onClick={() => onChange(tab.id)} type="button">{tab.label}</button>)}</div>; }

export function DataTable({ children, state }: { children: ReactNode; state?: "default" | "loading" | "empty" | "filtered-empty" | "error" }) { return <div className="min-w-0 overflow-hidden rounded-[var(--radius-card)] border border-border-subtle bg-surface-1 shadow-[var(--shadow-card)]"><div className="sellora-scrollbar min-w-0 overflow-x-auto">{state && state !== "default" ? <StatePanel state={state} /> : children}</div></div>; }
function StatePanel({ state }: { state: Exclude<NonNullable<Parameters<typeof DataTable>[0]["state"]>, "default"> }) { const copy = { loading: ["Завантаження даних…", "Підготовлюємо таблицю."], empty: ["Даних ще немає", "Створіть перший запис або імпортуйте історичні дані."], "filtered-empty": ["Нічого не знайдено", "Спробуйте змінити фільтри або пошуковий запит."], error: ["Не вдалося завантажити таблицю", "Оновіть сторінку або спробуйте пізніше."] }[state]; return <div className="grid min-h-56 place-items-center p-6 text-center"><div><Inbox className="mx-auto h-8 w-8 text-text-muted" /><h3 className="mt-3 font-black text-text-primary">{copy[0]}</h3><p className="mt-1 text-sm text-text-secondary">{copy[1]}</p></div></div>; }
export function Pagination({ page, totalPages, onPrev, onNext }: { page: number; totalPages: number; onPrev: () => void; onNext: () => void }) { return <div className="flex items-center justify-between gap-3 text-sm font-bold text-text-secondary"><Button variant="secondary" size="sm" onClick={onPrev} disabled={page <= 1}><ChevronLeft className="h-4 w-4" />Назад</Button><span>{page} / {Math.max(totalPages, 1)}</span><Button variant="secondary" size="sm" onClick={onNext} disabled={page >= totalPages}>Далі<ChevronRight className="h-4 w-4" /></Button></div>; }
export function Toast({ children, tone = "success" }: { children: ReactNode; tone?: "success" | "danger" | "info" }) { const Icon = tone === "success" ? Check : AlertCircle; return <div className="inline-flex max-w-sm items-center gap-3 rounded-2xl border border-border-subtle bg-surface-2 px-4 py-3 text-sm font-bold text-text-primary shadow-[var(--shadow-overlay)]"><Icon className="h-4 w-4" />{children}</div>; }
export { LoadingSkeleton, EmptyState, ErrorState } from "@/components/ui/states";
