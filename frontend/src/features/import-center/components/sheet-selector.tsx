"use client";

import { useI18n } from "@/i18n/provider";
export function SheetSelector({ sheets, value, onChange }: { sheets: string[]; value: string; onChange: (sheet: string) => void }) { const { t } = useI18n(); return <select className="w-full min-w-0 max-w-full truncate rounded-md border border-slate-300 px-3 py-2" value={value} onChange={(event) => onChange(event.target.value)}><option value="">{t("importCenter.selectSheet")}</option>{sheets.map((sheet) => <option key={sheet} value={sheet}>{sheet}</option>)}</select>; }
