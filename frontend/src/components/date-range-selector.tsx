"use client";

import { useMemo, useState } from "react";
import { dateRangeForPreset, dateRangePresetKeys, DateRangePreset, DateRangeValue } from "@/lib/date-range-presets";
import { useI18n } from "@/i18n/provider";
import { useDateRange } from "@/providers/date-range-provider";

export function DateRangeSelector({ compact = false, onChange }: { compact?: boolean; onChange?: (range: DateRangeValue) => void }) {
  const { t, locale } = useI18n();
  const sharedRange = useDateRange();
  const [localRange, setLocalRange] = useState<DateRangeValue>(() => dateRangeForPreset("last30"));
  const range = onChange ? localRange : sharedRange.range;
  const dateHelper = useMemo(() => (locale === "uk" ? "дд.мм.рррр" : "yyyy-mm-dd"), [locale]);

  function update(next: DateRangeValue) {
    if (onChange) {
      setLocalRange(next);
      onChange(next);
      return;
    }
    sharedRange.setRange(next);
  }

  return (
    <div className={`date-range-selector flex min-w-0 shrink-0 flex-col gap-2 sm:flex-row sm:items-center ${compact ? "w-full" : "hidden lg:flex"}`}>
      <select className="h-12 min-w-0 rounded-2xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 shadow-sm dark:border-white/10 dark:bg-white/10 dark:text-white" aria-label={t("dateRange.label")} value={range.preset} onChange={(event) => update(dateRangeForPreset(event.target.value as DateRangePreset))}>
        {dateRangePresetKeys().map((preset) => <option key={preset} value={preset}>{t(`dateRange.${preset}`)}</option>)}
      </select>
      {range.preset === "custom" ? (
        <div className="date-range-mobile-custom grid min-w-0 gap-2 sm:flex sm:items-center" aria-label={t("dateRange.mobile.customTitle")}>
          <label className="sr-only" htmlFor="global-date-from">{t("dateRange.dateFrom")}</label>
          <input id="global-date-from" className="sellora-date-input h-12 w-full min-w-0 rounded-2xl border border-slate-200 bg-white px-3 text-sm text-slate-700 shadow-sm dark:border-white/10 dark:bg-white/10 dark:text-white sm:w-36" type="date" value={range.date_from} title={`${t("dateRange.dateFrom")} · ${dateHelper}`} onChange={(event) => update({ ...range, date_from: event.target.value })} />
          <label className="sr-only" htmlFor="global-date-to">{t("dateRange.dateTo")}</label>
          <input id="global-date-to" className="sellora-date-input h-12 w-full min-w-0 rounded-2xl border border-slate-200 bg-white px-3 text-sm text-slate-700 shadow-sm dark:border-white/10 dark:bg-white/10 dark:text-white sm:w-36" type="date" value={range.date_to} title={`${t("dateRange.dateTo")} · ${dateHelper}`} onChange={(event) => update({ ...range, date_to: event.target.value })} />
        </div>
      ) : null}
    </div>
  );
}
