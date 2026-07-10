import type { ComponentPropsWithoutRef, ElementType, ReactNode } from "react";
import { cn } from "@/services/utils";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md" | "lg" | "icon";

const buttonVariants: Record<ButtonVariant, string> = {
  primary: "border-transparent bg-primary text-primary-foreground shadow-sellora-sm hover:bg-primary/90 focus-visible:ring-primary/25",
  secondary: "border-border bg-card text-card-foreground shadow-sellora-xs hover:border-primary/30 hover:text-primary focus-visible:ring-primary/20",
  ghost: "border-transparent bg-transparent text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:ring-primary/20",
  danger: "border-transparent bg-destructive text-destructive-foreground shadow-sellora-sm hover:bg-destructive/90 focus-visible:ring-destructive/20",
};

const buttonSizes: Record<ButtonSize, string> = {
  sm: "min-h-9 rounded-xl px-3 text-xs",
  md: "min-h-11 rounded-2xl px-4 text-sm",
  lg: "min-h-12 rounded-2xl px-5 text-base",
  icon: "h-11 w-11 rounded-2xl p-0",
};

export function Button({ className, variant = "primary", size = "md", ...props }: ComponentPropsWithoutRef<"button"> & { variant?: ButtonVariant; size?: ButtonSize }) {
  return (
    <button
      className={cn(
        "inline-flex shrink-0 items-center justify-center gap-2 border font-black transition focus-visible:outline-none focus-visible:ring-4 disabled:pointer-events-none disabled:opacity-50",
        buttonVariants[variant],
        buttonSizes[size],
        className,
      )}
      {...props}
    />
  );
}

export function Card({ className, ...props }: ComponentPropsWithoutRef<"section">) {
  return <section className={cn("sellora-card rounded-[var(--radius-card)] border border-border bg-card text-card-foreground shadow-sellora-md", className)} {...props} />;
}

export function PageHeader({ eyebrow, title, description, actions, className }: { eyebrow?: string; title: string; description?: string; actions?: ReactNode; className?: string }) {
  return (
    <header className={cn("flex min-w-0 flex-col gap-4 sm:flex-row sm:items-end sm:justify-between", className)}>
      <div className="min-w-0">
        {eyebrow ? <p className="text-xs font-black uppercase tracking-[0.2em] text-primary">{eyebrow}</p> : null}
        <h1 className="mt-1 break-words text-2xl font-black tracking-tight text-foreground sm:text-3xl">{title}</h1>
        {description ? <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{description}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}

export function StatusPill({ children, tone = "neutral", className }: { children: ReactNode; tone?: "neutral" | "success" | "warning" | "danger" | "info"; className?: string }) {
  const tones = {
    neutral: "bg-muted text-muted-foreground ring-border",
    success: "bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-200 dark:ring-emerald-400/20",
    warning: "bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-200 dark:ring-amber-400/20",
    danger: "bg-rose-50 text-rose-700 ring-rose-200 dark:bg-rose-500/10 dark:text-rose-200 dark:ring-rose-400/20",
    info: "bg-blue-50 text-blue-700 ring-blue-200 dark:bg-blue-500/10 dark:text-blue-200 dark:ring-blue-400/20",
  };
  return <span className={cn("sellora-status-badge inline-flex items-center rounded-full px-2.5 py-1 text-xs font-black ring-1", tones[tone], className)}>{children}</span>;
}

type FieldProps<T extends ElementType> = {
  as?: T;
  label: string;
  hint?: string;
  error?: string;
  children?: ReactNode;
  className?: string;
} & Omit<ComponentPropsWithoutRef<T>, "as" | "children" | "className">;

export function FormField<T extends ElementType = "input">({ as, label, hint, error, children, className, ...props }: FieldProps<T>) {
  const Component = as ?? "input";
  return (
    <label className="grid gap-2 text-sm font-bold text-foreground">
      <span>{label}</span>
      {children ?? <Component className={cn("min-h-11 rounded-2xl border border-input bg-card px-3 py-2 text-sm text-foreground outline-none transition placeholder:text-muted-foreground focus:border-primary/50 focus:ring-4 focus:ring-primary/10", className)} {...props} />}
      {hint && !error ? <span className="text-xs font-semibold leading-5 text-muted-foreground">{hint}</span> : null}
      {error ? <span className="text-xs font-bold leading-5 text-destructive">{error}</span> : null}
    </label>
  );
}
