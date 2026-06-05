"use client";

import { ReactNode } from "react";

export function FormDialog({ title, description, children, onClose }: { title: string; description?: string; children: ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 overflow-y-auto overflow-x-hidden bg-slate-950/60 p-3 backdrop-blur-sm sm:p-4">
      <div className="mx-auto flex min-h-full w-full max-w-2xl items-center justify-center">
        <section className="max-h-[calc(100dvh-1.5rem)] w-full min-w-0 overflow-y-auto overflow-x-hidden rounded-3xl border border-slate-200 bg-white p-5 shadow-2xl dark:border-white/10 dark:bg-slate-900 sm:p-6">
          <div className="mb-5 flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <h2 className="text-xl font-black text-slate-950 dark:text-white">{title}</h2>
              {description ? <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">{description}</p> : null}
            </div>
            <button className="min-h-11 rounded-xl border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700 dark:border-white/10 dark:text-slate-100" onClick={onClose} type="button">Close</button>
          </div>
          {children}
        </section>
      </div>
    </div>
  );
}
