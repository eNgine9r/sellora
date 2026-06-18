"use client";

import { ChangeEvent, type ReactNode } from "react";
import { useI18n } from "@/i18n/provider";

type Option = { value: string; label: string };
const inputClass = "min-h-11 w-full min-w-0 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition focus:border-violet-300 focus:ring-4 focus:ring-violet-100 dark:border-white/10 dark:bg-white/10 dark:text-white dark:placeholder:text-slate-400";

export function FilterBar({ children }: { children: ReactNode }) {
  return <section className="grid min-w-0 max-w-full gap-3 overflow-hidden rounded-2xl bg-white p-4 shadow-sm dark:bg-[#15172A] sm:grid-cols-2 lg:grid-cols-4">{children}</section>;
}

export function SearchInput({ value, onChange, placeholder, ariaLabel }: { value: string; onChange: (value: string) => void; placeholder: string; ariaLabel?: string }) {
  return <input className={inputClass} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} aria-label={ariaLabel ?? placeholder} />;
}

export function SortSelect({ value, onChange, options, label }: { value: string; onChange: (value: string) => void; options: Option[]; label?: string }) {
  const { t } = useI18n();
  return <select className={inputClass} value={value} onChange={(event: ChangeEvent<HTMLSelectElement>) => onChange(event.target.value)} aria-label={label ?? t("filters.sort")}>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select>;
}

export function ResetFiltersButton({ onClick }: { onClick: () => void }) {
  const { t } = useI18n();
  return <button className="min-h-11 rounded-xl border border-slate-200 bg-white px-4 text-sm font-bold text-slate-700 shadow-sm transition hover:border-violet-200 hover:text-violet-700 dark:border-white/10 dark:bg-white/10 dark:text-slate-100" type="button" onClick={onClick}>{t("filters.reset")}</button>;
}
