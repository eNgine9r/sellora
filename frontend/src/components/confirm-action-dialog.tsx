"use client";

export function ConfirmActionDialog({ title, description, actionLabel, isSubmitting = false, error, onCancel, onConfirm }: { title: string; description: string; actionLabel: string; isSubmitting?: boolean; error?: string | null; onCancel: () => void; onConfirm: () => void }) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto overflow-x-hidden bg-slate-950/50 p-3 sm:p-4">
      <div className="max-h-[calc(100dvh-1.5rem)] w-full max-w-lg overflow-y-auto overflow-x-hidden rounded-2xl bg-white p-5 shadow-xl sm:p-6">
        <h2 className="text-xl font-bold text-slate-950">{title}</h2>
        <p className="mt-3 text-sm leading-6 text-slate-600">{description}</p>
        {error ? <p className="mt-4 rounded-lg bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700">{error}</p> : null}
        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          <button className="min-h-11 rounded-xl border border-slate-300 px-4 py-2 font-bold text-slate-700" disabled={isSubmitting} onClick={onCancel} type="button">
            Cancel
          </button>
          <button className="min-h-11 rounded-xl bg-rose-600 px-4 py-2 font-bold text-white disabled:cursor-not-allowed disabled:opacity-60" disabled={isSubmitting} onClick={onConfirm} type="button">
            {isSubmitting ? "Working…" : actionLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
