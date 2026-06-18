"use client";

import { createContext, PropsWithChildren, useContext, useMemo, useState } from "react";
import { dateRangeForPreset, DateRangeValue, previousDateRange } from "@/lib/date-range-presets";

type DateRangeContextValue = {
  range: DateRangeValue;
  previousRange: DateRangeValue;
  setRange: (range: DateRangeValue) => void;
};

const DateRangeContext = createContext<DateRangeContextValue | null>(null);

export function DateRangeProvider({ children }: PropsWithChildren) {
  const [range, setRange] = useState<DateRangeValue>(() => dateRangeForPreset("last30"));
  const previousRangeValue = useMemo(() => previousDateRange(range), [range]);
  return <DateRangeContext.Provider value={{ range, previousRange: previousRangeValue, setRange }}>{children}</DateRangeContext.Provider>;
}

export function useDateRange() {
  const context = useContext(DateRangeContext);
  if (!context) throw new Error("useDateRange must be used within DateRangeProvider");
  return context;
}
