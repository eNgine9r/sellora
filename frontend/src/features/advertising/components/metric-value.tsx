export function MetricValue({ value, suffix = "" }: { value?: string | number | null; suffix?: string }) { return <span>{value ?? "—"}{value !== undefined && value !== null ? suffix : ""}</span>; }
