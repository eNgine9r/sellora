export type DateRangePreset = "today" | "last7" | "last30" | "thisMonth" | "allTime" | "custom";
export type DateRangeValue = { preset: DateRangePreset; date_from: string; date_to: string };

function isoDate(date: Date) {
  return date.toISOString().slice(0, 10);
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
  return ["today", "last7", "last30", "thisMonth", "allTime", "custom"];
}


export function previousDateRange(range: DateRangeValue): DateRangeValue {
  if (range.preset === "allTime" || !range.date_from || !range.date_to) return { preset: range.preset, date_from: "", date_to: "" };
  const start = new Date(`${range.date_from}T00:00:00Z`);
  const end = new Date(`${range.date_to}T00:00:00Z`);
  const days = Math.max(1, Math.round((end.getTime() - start.getTime()) / 86_400_000) + 1);
  const previousEnd = new Date(start);
  previousEnd.setDate(previousEnd.getDate() - 1);
  const previousStart = new Date(previousEnd);
  previousStart.setDate(previousStart.getDate() - (days - 1));
  return { preset: range.preset, date_from: isoDate(previousStart), date_to: isoDate(previousEnd) };
}
