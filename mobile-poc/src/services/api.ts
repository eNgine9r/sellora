import { fetch } from "expo/fetch";

import { tokenStore } from "@/services/token-store";

const API_URL = process.env.EXPO_PUBLIC_API_URL;

type ApiOptions = RequestInit & { workspaceOptional?: boolean };

export async function apiRequest<T>(path: string, options: ApiOptions = {}): Promise<T> {
  if (!API_URL) throw new Error("EXPO_PUBLIC_API_URL is not configured");
  const [token, workspaceId] = await Promise.all([tokenStore.getAccessToken(), tokenStore.getWorkspaceId()]);
  if (!options.workspaceOptional && !workspaceId) throw new Error("Workspace is not selected");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20_000);
  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(workspaceId ? { "X-Workspace-ID": workspaceId } : {}),
        ...options.headers,
      },
    });
    if (!response.ok) throw new Error(`Sellora API error ${response.status}`);
    return (await response.json()) as T;
  } finally {
    clearTimeout(timeout);
  }
}
