/** Kyiv-local day keys; never derive business dates with UTC toISOString(). */
export function kyivDateKey(date = new Date()): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Europe/Kyiv", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(date);
  const get = (type: string) => parts.find((part) => part.type === type)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")}`;
}
export function localDayKey(timestamp: string): string {
  return kyivDateKey(new Date(timestamp));
}
export function dateLabel(day: string, locale: string, opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "long" }) {
  const [y, m, d] = day.split("-").map(Number);
  return new Intl.DateTimeFormat(locale === "uk" ? "uk-UA" : "en-US", opts).format(new Date(Date.UTC(y, m - 1, d, 12)));
}
export function monthKey(year: number, monthZero: number): string {
  return `${year}-${String(monthZero + 1).padStart(2, "0")}`;
}
