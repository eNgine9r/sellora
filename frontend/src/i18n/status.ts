import { Locale, messages, defaultLocale } from "@/i18n/config";

export function formatEnumStatus(group: keyof typeof messages.uk.statuses, value: string, locale: Locale = defaultLocale) {
  const localized = messages[locale].statuses[group]?.[value as keyof typeof messages.uk.statuses[typeof group]];
  return typeof localized === "string" ? localized : value.replaceAll("_", " ");
}
