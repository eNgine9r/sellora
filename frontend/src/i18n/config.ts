import uk from "@/i18n/messages/uk.json";
import en from "@/i18n/messages/en.json";

export const defaultLocale = "uk" as const;
export const localeStorageKey = "sellora_locale" as const;
export const locales = ["uk", "en"] as const;
export type Locale = (typeof locales)[number];
export type Messages = typeof uk;

export const messages: Record<Locale, Messages> = { uk, en };

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (locales as readonly string[]).includes(value);
}
