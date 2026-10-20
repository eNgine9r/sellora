import { authStorage } from "@/services/auth.service";
import { fetchMetaAdsStatus, metaAdsRequest } from "@/services/meta-ads";
import type { MetaAdsStatus } from "@/types/meta-ads";

type AdsCallback = { code: string | null; state: string | null; denied: boolean };
declare global { interface Window { __selloraMetaAdsCallback?: AdsCallback } }
export function takeAdsCallback(): AdsCallback {
  const captured = window.__selloraMetaAdsCallback;
  delete window.__selloraMetaAdsCallback;
  if (captured) return captured;
  const params = new URLSearchParams(window.location.search);
  return { code: params.get("code"), state: params.get("state"), denied: params.has("error") };
}

const key = "sellora.meta-ads.intent";
export type AdsIntent = { actor: string; workspace: string; state: string; expires: string; phase: "pending" | "processing" | "complete" };
export function readAdsIntent(): AdsIntent | null {
  try { return JSON.parse(sessionStorage.getItem(key) ?? "null") as AdsIntent | null; } catch { return null; }
}
export function clearAdsIntent(expectedState?: string) {
  if (!expectedState || readAdsIntent()?.state === expectedState) sessionStorage.removeItem(key);
}
export function saveAdsIntent(intent: AdsIntent) { sessionStorage.setItem(key, JSON.stringify(intent)); }
export function matchesAdsIntent(intent: AdsIntent, actor: string, workspace: string) {
  return intent.actor === actor && intent.workspace === workspace && authStorage.getCurrentWorkspaceId() === workspace && authStorage.getCurrentActorId() === actor;
}
// Only the promise is shared during StrictMode remounts. Codes stay in memory.
const exchanges = new Map<string, Promise<MetaAdsStatus>>();
export function completeAdsIntent(intent: AdsIntent, code: string | null, state: string | null) {
  // Reject unassociated arrivals before joining or consuming any stored attempt.
  // A query-free visit may recover an already processing/completed attempt only.
  if ((code !== null || state !== null || intent.phase === "pending") && state !== intent.state) {
    return Promise.reject(new Error("invalid_state"));
  }
  const attempt = intent.actor + ":" + intent.workspace + ":" + intent.state;
  const existing = exchanges.get(attempt);
  if (existing) return existing;
  const exchange = (async () => {
    if (intent.phase !== "pending") {
      const status = await fetchMetaAdsStatus(intent.workspace);
      if (!status.connected) throw new Error("invalid_state");
      return status;
    }
    if (!code || Date.parse(intent.expires) <= Date.now()) {
      clearAdsIntent(intent.state); // The incoming state matched this attempt above.
      throw new Error("invalid_state");
    }
    saveAdsIntent({ ...intent, phase: "processing" });
    try {
      const status = await metaAdsRequest<MetaAdsStatus>(intent.workspace, "/oauth/callback", { code, state });
      if (matchesAdsIntent(intent, intent.actor, intent.workspace) && readAdsIntent()?.state === intent.state) saveAdsIntent({ ...intent, phase: "complete" });
      return status;
    } catch (error) {
      clearAdsIntent(intent.state);
      throw error;
    }
  })();
  exchanges.set(attempt, exchange);
  void exchange.finally(() => { exchanges.delete(attempt); }).catch(() => {});
  return exchange;
}
