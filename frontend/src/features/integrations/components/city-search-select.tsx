"use client";
import { useQuery } from "@tanstack/react-query";
import { safeApiErrorMessage } from "@/services/api";
import { searchNovaPoshtaCities } from "@/services/integrations";
import { NovaPoshtaDirectoryItem } from "@/types/integrations";
import { useI18n } from "@/i18n/provider";

export function CitySearchSelect({ workspaceId, query, onQuery, onSelect, label, helperText }: { workspaceId: string; query: string; onQuery: (value: string) => void; onSelect: (item: NovaPoshtaDirectoryItem) => void; label?: string; helperText?: string }) {
  const { t } = useI18n();
  const cities = useQuery({ queryKey: ["np-cities", workspaceId, query], queryFn: () => searchNovaPoshtaCities(workspaceId, query), enabled: query.trim().length >= 2 });
  return <label className="grid gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200"><span>{label ?? t("novaPoshta.searchSenderCity")}</span><input className="min-h-11 rounded-lg border border-slate-300 px-3 dark:border-white/10 dark:bg-white/10 dark:text-white" value={query} onChange={(event) => onQuery(event.target.value)} placeholder={t("novaPoshta.searchCityPlaceholder")} />{helperText ? <span className="text-xs font-normal text-slate-500 dark:text-slate-400">{helperText}</span> : null}{cities.isError ? <span className="rounded-lg bg-amber-50 px-3 py-2 text-xs font-bold text-amber-700 dark:bg-amber-500/15 dark:text-amber-100">{safeApiErrorMessage(cities.error, t("novaPoshta.citySearchFailed"))}</span> : null}{cities.isFetching ? <span className="text-xs font-normal text-slate-500 dark:text-slate-400">{t("novaPoshta.searchingCities")}</span> : null}{cities.isSuccess && query.trim().length >= 2 && !cities.isFetching && !cities.data?.length ? <span className="text-xs font-normal text-slate-500 dark:text-slate-400">{t("novaPoshta.noCitiesFound")}</span> : null}{cities.data?.length ? <div className="sellora-scrollbar grid max-h-44 gap-1 overflow-y-auto rounded-lg border border-slate-200 bg-white p-2 dark:border-white/10 dark:bg-slate-950">{cities.data.map((city) => <button className="rounded-md px-2 py-2 text-left text-sm hover:bg-slate-50 dark:hover:bg-white/10" key={city.ref} type="button" onClick={() => onSelect(city)}>{city.description}</button>)}</div> : null}</label>;
}
