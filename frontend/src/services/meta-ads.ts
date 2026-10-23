import { apiRequest, ApiError } from "@/services/api";
import type { MetaAdsAccounts, MetaAdsStatus, MetaAdsSync } from "@/types/meta-ads";

export function metaAdsRequest<T>(workspaceId: string, path: string, body?: object) {
  return apiRequest<T>("/integrations/meta-ads" + path, {
    headers: { "X-Workspace-ID": workspaceId },
    ...(body ? { method: "POST", body: JSON.stringify(body) } : {}),
  });
}
export const fetchMetaAdsStatus = (id: string) => metaAdsRequest<MetaAdsStatus>(id, "/status");
export const fetchMetaAdsAccounts = (id: string) => metaAdsRequest<MetaAdsAccounts>(id, "/accounts");
export const startMetaAds = (id: string) => metaAdsRequest<MetaAdsStatus & { authorization_url: string; state_expires_at: string }>(id, "/oauth/start", {});
export const selectMetaAdsAccount = (id: string, external_account_id: string) => metaAdsRequest<MetaAdsStatus>(id, "/account", { external_account_id });
export const syncMetaAds = (id: string, date_from: string, date_to: string) => metaAdsRequest<MetaAdsSync>(id, "/sync", { date_from, date_to });
export const disconnectMetaAds = (id: string) => metaAdsRequest<MetaAdsStatus>(id, "/disconnect", {});
export function integrationErrorCode(error: unknown): string {
  if (!(error instanceof ApiError)) return "failed";
  const detail = (error.detail as { detail?: { code?: string } } | null)?.detail;
  return typeof detail?.code === "string" ? detail.code : error.status === 403 ? "ownerOnly" : "failed";
}
