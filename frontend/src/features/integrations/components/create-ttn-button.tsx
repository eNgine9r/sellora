"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { safeApiErrorMessage } from "@/services/api";
import { createNovaPoshtaTtn, syncNovaPoshtaStatus } from "@/services/integrations";

export function CreateTtnButton({ workspaceId, shipmentId }: { workspaceId: string; shipmentId: string }) {
  const queryClient = useQueryClient();
  const [message, setMessage] = useState<string | null>(null);
  const create = useMutation({ mutationFn: () => createNovaPoshtaTtn(workspaceId, shipmentId), onSuccess: (result) => { setMessage(result.success ? result.message : `${result.message} ${result.errors?.join(", ") ?? ""}`); queryClient.invalidateQueries({ queryKey: ["shipments", workspaceId] }); }, onError: (error) => setMessage(safeApiErrorMessage(error, "Unable to create Nova Poshta TTN.")) });
  const sync = useMutation({ mutationFn: () => syncNovaPoshtaStatus(workspaceId, shipmentId), onSuccess: (result) => { setMessage(result.message); queryClient.invalidateQueries({ queryKey: ["shipments", workspaceId] }); }, onError: (error) => setMessage(safeApiErrorMessage(error, "Unable to sync Nova Poshta status.")) });
  return <div className="grid gap-2"><div className="grid gap-2 sm:grid-cols-2"><button className="min-h-11 rounded-xl bg-blue-600 px-4 py-2 font-bold text-white disabled:opacity-60" disabled={create.isPending} onClick={() => create.mutate()}>Create Nova Poshta TTN</button><button className="min-h-11 rounded-xl border border-slate-300 px-4 py-2 font-bold disabled:opacity-60" disabled={sync.isPending} onClick={() => sync.mutate()}>Sync Nova Poshta Status</button></div>{message ? <p className="rounded-lg bg-blue-50 p-3 text-sm font-semibold text-blue-700">{message}</p> : null}</div>;
}
