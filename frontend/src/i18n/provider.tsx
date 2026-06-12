"use client";

import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";
import { defaultLocale, isLocale, Locale, localeStorageKey, messages } from "@/i18n/config";

type Primitive = string | number | boolean | null | undefined;
type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, values?: Record<string, Primitive>) => string;
  tr: <T = unknown>(key: string) => T;
  formatStatus: (group: string, value?: string | null) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);

function readPath(source: unknown, key: string): unknown {
  return key.split(".").reduce<unknown>((current, part) => (current && typeof current === "object" ? (current as Record<string, unknown>)[part] : undefined), source);
}

function interpolate(value: string, values?: Record<string, Primitive>) {
  if (!values) return value;
  return value.replace(/\{(\w+)\}/g, (_, name: string) => String(values[name] ?? ""));
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(defaultLocale);

  useEffect(() => {
    const saved = window.localStorage.getItem(localeStorageKey);
    setLocaleState(isLocale(saved) ? saved : defaultLocale);
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dataset.locale = locale;
    window.localStorage.setItem(localeStorageKey, locale);
  }, [locale]);

  const value = useMemo<I18nContextValue>(() => {
    const t = (key: string, values?: Record<string, Primitive>) => {
      const translated = readPath(messages[locale], key) ?? readPath(messages[defaultLocale], key);
      return interpolate(typeof translated === "string" ? translated : key, values);
    };
    const tr = <T,>(key: string) => (readPath(messages[locale], key) ?? readPath(messages[defaultLocale], key)) as T;
    const formatStatus = (group: string, status?: string | null) => {
      if (!status) return "";
      const key = `statuses.${group}.${status}`;
      const label = t(key);
      return label === key ? status.replaceAll("_", " ") : label;
    };
    return { locale, setLocale: setLocaleState, t, tr, formatStatus };
  }, [locale]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const value = useContext(I18nContext);
  if (!value) throw new Error("useI18n must be used within LocaleProvider");
  return value;
}
