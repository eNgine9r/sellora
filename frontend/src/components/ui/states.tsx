import type { ReactNode } from "react";
import { AlertCircle, Inbox } from "lucide-react";

export function LoadingSkeleton({ rows = 3, title = "Loading data…" }: { rows?: number; title?: string }) {
  return (
    <section className="rounded-[24px] border border-slate-100 bg-white p-5 shadow-[0_18px_45px_rgba(15,23,42,0.06)]">
      <div className="mb-5 flex items-center justify-between gap-4">
        <div>
          <div className="h-4 w-28 animate-pulse rounded-full bg-slate-100" />
          <p className="mt-3 text-sm font-semibold text-slate-400">{title}</p>
        </div>
        <div className="h-10 w-24 animate-pulse rounded-2xl bg-slate-100" />
      </div>
      <div className="grid gap-3">
        {Array.from({ length: rows }).map((_, index) => (
          <div key={index} className="h-14 animate-pulse rounded-2xl bg-slate-100/80" />
        ))}
      </div>
    </section>
  );
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <div className="grid min-h-44 place-items-center rounded-[20px] border border-dashed border-slate-200 bg-slate-50/70 p-6 text-center">
      <div>
        <div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-white text-violet-600 shadow-sm">
          <Inbox className="h-5 w-5" />
        </div>
        <h3 className="mt-4 text-base font-black text-slate-900">{title}</h3>
        <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">{description}</p>
        {action ? <div className="mt-4">{action}</div> : null}
      </div>
    </div>
  );
}

export function ErrorState({ title = "Something went wrong", description, onRetry }: { title?: string; description: string; onRetry?: () => void }) {
  return (
    <div className="rounded-[24px] border border-rose-100 bg-rose-50 p-5 text-rose-900 shadow-[0_18px_45px_rgba(190,18,60,0.08)]">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-3">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-white text-rose-600 shadow-sm">
            <AlertCircle className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-black">{title}</h3>
            <p className="mt-1 text-sm leading-6 text-rose-700">{description}</p>
          </div>
        </div>
        {onRetry ? (
          <button className="min-h-11 rounded-2xl bg-white px-4 text-sm font-black text-rose-700 shadow-sm" onClick={onRetry}>
            Try again
          </button>
        ) : null}
      </div>
    </div>
  );
}
