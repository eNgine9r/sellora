import type { ReactNode } from "react";
import { AlertCircle, Inbox } from "lucide-react";

export function LoadingSkeleton({ rows = 3, title = "Завантаження даних…" }: { rows?: number; title?: string }) {
  return (
    <section className="rounded-[var(--radius-card)] border border-border bg-card p-5 text-card-foreground shadow-sellora-md">
      <div className="mb-5 flex items-center justify-between gap-4">
        <div>
          <div className="h-4 w-28 animate-pulse rounded-full bg-muted" />
          <p className="mt-3 text-sm font-semibold text-muted-foreground">{title}</p>
        </div>
        <div className="h-10 w-24 animate-pulse rounded-2xl bg-muted" />
      </div>
      <div className="grid gap-3">
        {Array.from({ length: rows }).map((_, index) => (
          <div key={index} className="h-14 animate-pulse rounded-2xl bg-muted/80" />
        ))}
      </div>
    </section>
  );
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <div className="grid min-h-44 place-items-center rounded-[20px] border border-dashed border-border bg-muted/60 p-6 text-center">
      <div>
        <div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-card text-primary shadow-sellora-xs">
          <Inbox className="h-5 w-5" />
        </div>
        <h3 className="mt-4 text-base font-black text-foreground">{title}</h3>
        <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">{description}</p>
        {action ? <div className="mt-4">{action}</div> : null}
      </div>
    </div>
  );
}

export function ErrorState({ title = "Щось пішло не так", description, onRetry }: { title?: string; description: string; onRetry?: () => void }) {
  return (
    <div className="rounded-[24px] border border-destructive/20 bg-destructive/10 p-5 text-destructive shadow-sellora-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-3">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-card text-destructive shadow-sellora-xs">
            <AlertCircle className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-black">{title}</h3>
            <p className="mt-1 text-sm leading-6 text-destructive">{description}</p>
          </div>
        </div>
        {onRetry ? (
          <button className="min-h-11 rounded-2xl bg-card px-4 text-sm font-black text-destructive shadow-sellora-xs" onClick={onRetry}>
            Спробувати ще раз
          </button>
        ) : null}
      </div>
    </div>
  );
}
