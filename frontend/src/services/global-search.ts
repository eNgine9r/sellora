import { apiRequest } from "@/services/api";

export type GlobalSearchKind = "orders" | "customers" | "leads" | "products" | "shipments";
export type GlobalSearchResult = {
  kind: GlobalSearchKind;
  id: string;
  title: string;
  subtitle: string;
  href: string;
};

export function searchWorkspaceRecords(workspaceId: string, query: string, signal?: AbortSignal) {
  const normalized = query.trim().slice(0, 80);
  if (!workspaceId || normalized.length < 2) return Promise.resolve([] as GlobalSearchResult[]);
  return apiRequest<GlobalSearchResult[]>(`/search?q=${encodeURIComponent(normalized)}`, {
    headers: { "X-Workspace-ID": workspaceId },
    signal,
  });
}
