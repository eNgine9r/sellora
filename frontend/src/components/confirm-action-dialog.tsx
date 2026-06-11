"use client";

export function ConfirmActionDialog({ title, description, actionLabel, isSubmitting = false, error, onCancel, onConfirm }: { title: string; description: string; actionLabel: string; isSubmitting?: boolean; error?: string | null; onCancel: () => void; onConfirm: () => void }) {
  return (
    <div className="sellora-dialog-overlay fixed inset-0 z-50 overflow-y-auto overflow-x-hidden bg-slate-950/60 p-3 backdrop-blur-sm sm:p-4">
      <div className="mx-auto flex min-h-full w-full items-center justify-center mobile-safe-bottom">
        <section className="sellora-dialog-panel max-h-[calc(100dvh-1.5rem)] w-[calc(100vw-1.5rem)] max-w-[420px] min-w-0 overflow-y-auto overflow-x-hidden rounded-3xl border border-slate-200 bg-white p-5 shadow-2xl dark:border-white/10 dark:bg-slate-900 sm:w-full sm:max-h-[calc(100dvh-3rem)] sm:p-6">
          <h2 className="break-words text-xl font-black text-slate-950 dark:text-white">{title}</h2>
          <p className="mt-3 break-words text-sm leading-6 text-slate-600 dark:text-slate-300">{description}</p>
          {error ? <p className="mt-4 rounded-lg bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700 dark:bg-rose-500/15 dark:text-rose-100">{error}</p> : null}
          <div className="mt-6 grid min-w-0 gap-3 sm:grid-cols-2">
            <button className="min-h-11 rounded-xl border border-slate-300 px-4 py-2 font-bold text-slate-700 dark:border-white/10 dark:text-slate-100" disabled={isSubmitting} onClick={onCancel} type="button">
              Cancel
            </button>
            <button className="min-h-11 rounded-xl bg-rose-600 px-4 py-2 font-bold text-white disabled:cursor-not-allowed disabled:opacity-60" disabled={isSubmitting} onClick={onConfirm} type="button">
              {isSubmitting ? "Working…" : actionLabel}
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
