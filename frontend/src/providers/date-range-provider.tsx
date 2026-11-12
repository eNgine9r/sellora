"use client";

import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { dateRangeForPreset, DateRangeValue, previousDateRange, restoreDateRange } from "@/lib/date-range-presets";

export const DATE_RANGE_STORAGE_KEY = "sellora:date-range:v1";

type DateRangeContextValue = {
  range: DateRangeValue;
  previousRange: DateRangeValue;
  isReady: boolean;
  setRange: (range: DateRangeValue) => void;
};

const DateRangeContext = createContext<DateRangeContextValue | null>(null);

export function DateRangeProvider({ children }: PropsWithChildren) {
  // Date strings remain empty on SSR and initial hydration: server timezone
  // may differ from the user's timezone (especially around midnight).
  // The effect below resolves local calendar dates before enabling data queries.
  const [range, setRangeState] = useState<DateRangeValue>({ preset: "thisMonth", date_from: "", date_to: "" });
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    try {
      setRangeState(restoreDateRange(window.localStorage.getItem(DATE_RANGE_STORAGE_KEY)));
    } catch {
      setRangeState(dateRangeForPreset("thisMonth"));
    }
    setIsReady(true);
  }, []);

  const setRange = useCallback((next: DateRangeValue) => {
    setRangeState(next);
    try {
      // Persist the preset, and preserve exact dates only for Custom.
      // Dynamic presets are always recomputed for the current day on restore.
      const saved = next.preset === "custom" ? next : { preset: next.preset };
      window.localStorage.setItem(DATE_RANGE_STORAGE_KEY, JSON.stringify(saved));
    } catch {
      // Private browsing / storage denial must not block changing the period.
    }
  }, []);

  useEffect(() => {
    if (!isReady) return;
    const refreshRollingPreset = () => {
      setRangeState((previous) => {
        if (previous.preset === "custom") return previous;
        const next = dateRangeForPreset(previous.preset);
        return next.date_from === previous.date_from && next.date_to === previous.date_to ? previous : next;
      });
    };
    window.addEventListener("focus", refreshRollingPreset);
    document.addEventListener("visibilitychange", refreshRollingPreset);
    return () => {
      window.removeEventListener("focus", refreshRollingPreset);
      document.removeEventListener("visibilitychange", refreshRollingPreset);
    };
  }, [isReady]);

  const previousRangeValue = useMemo(() => previousDateRange(range), [range]);
  const value = useMemo(() => ({
    range, previousRange: previousRangeValue, isReady, setRange,
  }), [range, previousRangeValue, isReady, setRange]);

  return <DateRangeContext.Provider value={value}>{children}</DateRangeContext.Provider>;
}

export function useDateRange() {
  const context = useContext(DateRangeContext);
  if (!context) throw new Error("useDateRange must be used within DateRangeProvider");
  return context;
}
