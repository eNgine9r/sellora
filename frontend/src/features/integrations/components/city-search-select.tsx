"use client";
import { useQuery } from "@tanstack/react-query";
import { searchNovaPoshtaCities } from "@/services/integrations";
import { NovaPoshtaDirectoryItem } from "@/types/integrations";

export function CitySearchSelect({ workspaceId, query, onQuery, onSelect }: { workspaceId: string; query: string; onQuery: (value: string) => void; onSelect: (item: NovaPoshtaDirectoryItem) => void }) {
  const cities = useQuery({ queryKey: ["np-cities", workspaceId, query], queryFn: () => searchNovaPoshtaCities(workspaceId, query), enabled: query.trim().length >= 2 });
  return <div className="grid gap-2"><input className="min-h-11 rounded-lg border border-slate-300 px-3" value={query} onChange={(event) => onQuery(event.target.value)} placeholder="Search Nova Poshta city" />{cities.data?.length ? <div className="grid max-h-44 gap-1 overflow-y-auto rounded-lg border border-slate-200 bg-white p-2">{cities.data.map((city) => <button className="rounded-md px-2 py-2 text-left text-sm hover:bg-slate-50" key={city.ref} type="button" onClick={() => onSelect(city)}>{city.description}</button>)}</div> : null}</div>;
}
