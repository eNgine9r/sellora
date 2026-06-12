const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

type PrimitiveInput = string | number | boolean | null | undefined;

export function cleanOptionalString(value: PrimitiveInput): string | null {
  if (value === null || value === undefined) return null;
  const cleaned = String(value).trim();
  return cleaned.length > 0 ? cleaned : null;
}

export function cleanRequiredString(value: PrimitiveInput): string {
  return cleanOptionalString(value) ?? "";
}

export function cleanOptionalUuid(value: PrimitiveInput): string | null {
  const cleaned = cleanOptionalString(value);
  return cleaned && UUID_PATTERN.test(cleaned) ? cleaned : null;
}

function parseNumber(value: PrimitiveInput): number | null {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  const normalized = String(value).trim().replace(/\s+/g, "").replace(",", ".");
  if (!normalized) return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

export function cleanOptionalNumber(value: PrimitiveInput): number | null {
  return parseNumber(value);
}

export function cleanRequiredNumber(value: PrimitiveInput): number {
  return cleanOptionalNumber(value) ?? 0;
}

export function cleanOptionalInteger(value: PrimitiveInput): number | null {
  const parsed = parseNumber(value);
  return parsed === null ? null : Math.trunc(parsed);
}

export function cleanRequiredInteger(value: PrimitiveInput): number {
  return cleanOptionalInteger(value) ?? 0;
}

export function cleanOptionalDate(value: PrimitiveInput): string | null {
  const cleaned = cleanOptionalString(value);
  if (!cleaned) return null;
  const date = new Date(cleaned);
  if (Number.isNaN(date.getTime())) return null;
  return cleaned.length === 10 ? cleaned : date.toISOString();
}

export function cleanOptionalEnum<T extends string>(value: PrimitiveInput, allowedValues: readonly T[]): T | null {
  const cleaned = cleanOptionalString(value);
  return cleaned && (allowedValues as readonly string[]).includes(cleaned) ? cleaned as T : null;
}

export function stripUndefinedFields<T extends Record<string, unknown>>(payload: T): T {
  return Object.fromEntries(Object.entries(payload).filter(([, value]) => value !== undefined)) as T;
}

export function removeFrontendOnlyFields<T extends Record<string, unknown>, K extends keyof T>(payload: T, allowedKeys: readonly K[]): Pick<T, K> {
  const allowed = new Set<keyof T>(allowedKeys);
  return Object.fromEntries(Object.entries(payload).filter(([key]) => allowed.has(key as keyof T))) as Pick<T, K>;
}
