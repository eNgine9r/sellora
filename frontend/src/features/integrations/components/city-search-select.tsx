"use client";
import { useQuery } from "@tanstack/react-query";
import { safeApiErrorMessage } from "@/services/api";
import { searchNovaPoshtaCities } from "@/services/integrations";
import { NovaPoshtaDirectoryItem } from "@/types/integrations";

export function CitySearchSelect({ workspaceId, query, onQuery, onSelect, label = "Nova Poshta city", helperText }: { workspaceId: string; query: string; onQuery: (value: string) => void; onSelect: (item: NovaPoshtaDirectoryItem) => void; label?: string; helperText?: string }) {
  const cities = useQuery({ queryKey: ["np-cities", workspaceId, query], queryFn: () => searchNovaPoshtaCities(workspaceId, query), enabled: query.trim().length >= 2 });
  return <label className="grid gap-2 text-sm font-semibold text-slate-700"><span>{label}</span><input className="min-h-11 rounded-lg border border-slate-300 px-3" value={query} onChange={(event) => onQuery(event.target.value)} placeholder="Search Nova Poshta city" />{helperText ? <span className="text-xs font-normal text-slate-500">{helperText}</span> : null}{cities.isError ? <span className="rounded-lg bg-amber-50 px-3 py-2 text-xs font-bold text-amber-700">{safeApiErrorMessage(cities.error, "Unable to search Nova Poshta cities. Please try again.")}</span> : null}{cities.isFetching ? <span className="text-xs font-normal text-slate-500">Searching cities…</span> : null}{cities.data?.length ? <div className="grid max-h-44 gap-1 overflow-y-auto rounded-lg border border-slate-200 bg-white p-2">{cities.data.map((city) => <button className="rounded-md px-2 py-2 text-left text-sm hover:bg-slate-50" key={city.ref} type="button" onClick={() => onSelect(city)}>{city.description}</button>)}</div> : null}</label>;
}
