/** A manual value remains the source of truth, including while it is being edited. */
export function fulfillmentAmount(override: string | null, total: number): string {
  return override ?? String(total);
}

export function isNonNegativeAmount(value: string): boolean {
  return value.trim() !== "" && Number.isFinite(Number(value)) && Number(value) >= 0;
}

export function isConfirmedCost(value: string | number | null | undefined): boolean {
  return isNonNegativeAmount(String(value ?? ""));
}

export function isPositiveWholeQuantity(value: string): boolean {
  return value.trim() !== "" && Number.isSafeInteger(Number(value)) && Number(value) >= 1;
}
