"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { safeApiErrorMessage } from "@/services/api";
import { searchNovaPoshtaWarehouses } from "@/services/integrations";
import { NovaPoshtaDirectoryItem } from "@/types/integrations";
import { useI18n } from "@/i18n/provider";

function useDebouncedValue(value: string, delayMs = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timeout = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(timeout);
  }, [value, delayMs]);
  return debounced;
}

export function WarehouseSearchSelect({ workspaceId, cityRef, query, onQuery, onSelect, label, helperText }: { workspaceId: string; cityRef: string; query: string; onQuery: (value: string) => void; onSelect: (item: NovaPoshtaDirectoryItem) => void; label?: string; helperText?: string }) {
  const { t } = useI18n();
  const debouncedQuery = useDebouncedValue(query.trim());
  const warehouses = useQuery({ queryKey: ["np-warehouses", workspaceId, cityRef, debouncedQuery], queryFn: () => searchNovaPoshtaWarehouses(workspaceId, cityRef, debouncedQuery || undefined), enabled: Boolean(cityRef) });
  return <label className="grid gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200"><span>{label ?? t("novaPoshta.searchSenderWarehouse")}</span><input className="min-h-11 rounded-lg border border-slate-300 px-3 disabled:bg-slate-100 dark:border-white/10 dark:bg-white/10 dark:text-white dark:disabled:bg-white/5" value={query} onChange={(event) => onQuery(event.target.value)} placeholder={t("novaPoshta.searchWarehousePlaceholder")} disabled={!cityRef} />{helperText ? <span className="text-xs font-normal text-slate-500 dark:text-slate-400">{helperText}</span> : null}{!cityRef ? <span className="text-xs font-normal text-slate-500 dark:text-slate-400">{t("novaPoshta.selectCityFirst")}</span> : null}{warehouses.isError ? <span className="rounded-lg bg-amber-50 px-3 py-2 text-xs font-bold text-amber-700 dark:bg-amber-500/15 dark:text-amber-100">{safeApiErrorMessage(warehouses.error, t("novaPoshta.warehouseSearchFailed"))}</span> : null}{warehouses.isFetching ? <span className="text-xs font-normal text-slate-500 dark:text-slate-400">{t("novaPoshta.loadingWarehouses")}</span> : null}{warehouses.isSuccess && cityRef && !warehouses.isFetching && !warehouses.data?.length ? <span className="text-xs font-normal text-slate-500 dark:text-slate-400">{t("novaPoshta.noWarehousesFound")}</span> : null}{warehouses.data?.length ? <div className="sellora-scrollbar grid max-h-44 gap-1 overflow-y-auto rounded-lg border border-slate-200 bg-white p-2 dark:border-white/10 dark:bg-slate-950">{warehouses.data.map((warehouse) => <button className="rounded-md px-2 py-2 text-left text-sm hover:bg-slate-50 dark:hover:bg-white/10" key={warehouse.ref} type="button" onClick={() => onSelect(warehouse)}>{warehouse.description}</button>)}</div> : null}</label>;
}
