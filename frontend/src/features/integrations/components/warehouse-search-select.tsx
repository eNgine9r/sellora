"use client";
import { useQuery } from "@tanstack/react-query";
import { searchNovaPoshtaWarehouses } from "@/services/integrations";
import { NovaPoshtaDirectoryItem } from "@/types/integrations";

export function WarehouseSearchSelect({ workspaceId, cityRef, query, onQuery, onSelect }: { workspaceId: string; cityRef: string; query: string; onQuery: (value: string) => void; onSelect: (item: NovaPoshtaDirectoryItem) => void }) {
  const warehouses = useQuery({ queryKey: ["np-warehouses", workspaceId, cityRef, query], queryFn: () => searchNovaPoshtaWarehouses(workspaceId, cityRef, query || undefined), enabled: Boolean(cityRef) });
  return <div className="grid gap-2"><input className="min-h-11 rounded-lg border border-slate-300 px-3" value={query} onChange={(event) => onQuery(event.target.value)} placeholder="Search Nova Poshta warehouse" />{warehouses.data?.length ? <div className="grid max-h-44 gap-1 overflow-y-auto rounded-lg border border-slate-200 bg-white p-2">{warehouses.data.map((warehouse) => <button className="rounded-md px-2 py-2 text-left text-sm hover:bg-slate-50" key={warehouse.ref} type="button" onClick={() => onSelect(warehouse)}>{warehouse.description}</button>)}</div> : null}</div>;
}
