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
  if (preset === "allTime") return { preset, date_from: "", date_to: "" };
  if (preset === "custom") return { preset, date_from: "", date_to: "" };
  return { preset, date_from: isoDate(start), date_to: isoDate(end) };
}

export function dateRangePresetKeys(): DateRangePreset[] {
  return ["today", "last7", "last30", "thisMonth", "allTime", "custom"];
}
