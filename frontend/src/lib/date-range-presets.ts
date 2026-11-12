export type DateRangePreset = "today" | "last7" | "last30" | "thisMonth" | "allTime" | "custom";
export type DateRangeValue = { preset: DateRangePreset; date_from: string; date_to: string };

const PRESETS: readonly DateRangePreset[] = ["today", "last7", "last30", "thisMonth", "allTime", "custom"];

// Calendar dates are local (not UTC). toISOString() would shift the day near
// midnight in UTC+ and UTC- timezones and produce the wrong "This month" range.
function isoDate(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function dateRangeForPreset(preset: DateRangePreset, now = new Date()): DateRangeValue {
  const end = new Date(now);
  const start = new Date(now);
  if (preset === "today") return { preset, date_from: isoDate(start), date_to: isoDate(end) };
  if (preset === "last7") start.setDate(start.getDate() - 6);
  if (preset === "last30") start.setDate(start.getDate() - 29);
  if (preset === "thisMonth") start.setDate(1);
  if (preset === "allTime") return { preset, date_from: "1970-01-01", date_to: isoDate(end) };
  if (preset === "custom") return { preset, date_from: "", date_to: "" };
  return { preset, date_from: isoDate(start), date_to: isoDate(end) };
}

export function dateRangePresetKeys(): DateRangePreset[] {
  return [...PRESETS];
}

function validCalendarDate(value: unknown): value is string {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split("-").map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return parsed.getUTCFullYear() === year && parsed.getUTCMonth() === month - 1 && parsed.getUTCDate() === day;
}

export function restoreDateRange(saved: string | null, now = new Date()): DateRangeValue {
  const fallback = dateRangeForPreset("thisMonth", now);
  if (!saved) return fallback;
  try {
    const value: unknown = JSON.parse(saved);
    if (!value || typeof value !== "object" || Array.isArray(value)) return fallback;
    const candidate = value as Record<string, unknown>;
    if (!PRESETS.includes(candidate.preset as DateRangePreset)) return fallback;
    const preset = candidate.preset as DateRangePreset;
    // Rolling presets cannot reuse dates saved in a previous month.
    if (preset !== "custom") return dateRangeForPreset(preset, now);

    // An unfinished custom selection is not a valid period after reload.
    // Falling back is safer than requesting unbounded, all-time reports.
    if (!validCalendarDate(candidate.date_from) || !validCalendarDate(candidate.date_to)) return fallback;
    if (candidate.date_from > candidate.date_to) return fallback;
    return { preset, date_from: candidate.date_from, date_to: candidate.date_to };
  } catch {
    return fallback;
  }
}

export function previousDateRange(range: DateRangeValue): DateRangeValue {
  if (range.preset === "allTime" || !range.date_from || !range.date_to) return { preset: range.preset, date_from: "", date_to: "" };
  const start = new Date(`${range.date_from}T00:00:00Z`);
  const end = new Date(`${range.date_to}T00:00:00Z`);
  const days = Math.max(1, Math.round((end.getTime() - start.getTime()) / 86_400_000) + 1);
  const previousEnd = new Date(start);
  previousEnd.setUTCDate(previousEnd.getUTCDate() - 1);
  const previousStart = new Date(previousEnd);
  previousStart.setUTCDate(previousStart.getUTCDate() - (days - 1));
  return {
    preset: range.preset,
    date_from: previousStart.toISOString().slice(0, 10),
    date_to: previousEnd.toISOString().slice(0, 10),
  };
}
