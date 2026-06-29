export type CurrencyCode = "UAH" | "USD";

const SYMBOLS: Record<CurrencyCode, string> = { UAH: "₴", USD: "$" };

export function normalizeCurrencyCode(value?: string | null): CurrencyCode {
  return value === "USD" ? "USD" : "UAH";
}

export function formatMoney(value?: string | number | null, currencyCode?: string | null): string {
  const amount = Number(value ?? 0);
  const safeAmount = Number.isFinite(amount) ? amount : 0;
  const currency = normalizeCurrencyCode(currencyCode);
  return `${SYMBOLS[currency]}${safeAmount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
