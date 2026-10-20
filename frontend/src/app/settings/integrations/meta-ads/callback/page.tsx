"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { WorkspaceHeader, WorkspacePage } from "@/components/crm-workspace";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { clearAdsIntent, completeAdsIntent, matchesAdsIntent, readAdsIntent, takeAdsCallback } from "@/features/integrations/lib/meta-ads-intent";

export default function MetaAdsCallbackPage() {
  const { t } = useI18n();
  const auth = useAuth();
  // Effect capture survives StrictMode cleanup; no provider values are persisted.
  const payload = useRef<{ code: string | null; state: string | null; denied: boolean } | null>(null);
  const [result, setResult] = useState("processing");
  const [owner, setOwner] = useState<string | null>(null);
  useEffect(() => {
    if (!payload.current) {
      payload.current = takeAdsCallback();
    }
    window.history.replaceState(window.history.state, "", "/settings/integrations/meta-ads/callback");
    if (auth.status === "loading") return;
    const intent = readAdsIntent();
    if (intent && payload.current.state !== intent.state && (payload.current.code !== null || payload.current.state !== null || (intent.phase === "pending" && !payload.current.denied))) {
      setResult("invalid_state"); return;
    }
    if (auth.status !== "authenticated" || !intent || auth.currentWorkspace?.role !== "OWNER" || !matchesAdsIntent(intent, auth.currentUser?.id ?? "", auth.currentWorkspaceId ?? "")) {
      if (intent && payload.current.state === intent.state) clearAdsIntent(payload.current.state);
      setResult("invalid_state"); return;
    }
    setOwner(intent.workspace + ":" + intent.actor);
    if (payload.current.denied) {
      if (payload.current.state === intent.state) clearAdsIntent(payload.current.state);
      setResult("denied"); return;
    }
    let active = true;
    void completeAdsIntent(intent, payload.current.code, payload.current.state).then(() => {
      if (!active) return;
      if (matchesAdsIntent(intent, intent.actor, intent.workspace) && readAdsIntent()?.state === intent.state) setResult("success");
      else setResult("invalid_state");
    }).catch(() => { if (!active) return; setResult("invalid_state"); }).finally(() => { payload.current = { code: null, state: null, denied: false }; });
    return () => { active = false; };
  }, [auth.status, auth.currentUser?.id, auth.currentWorkspaceId, auth.currentWorkspace?.role]);
  const visible = owner && owner !== auth.currentWorkspaceId + ":" + auth.currentUser?.id ? "invalid_state" : result;
  return <WorkspacePage><WorkspaceHeader eyebrow="Meta Ads" title={t("adsLive.callbackTitle")} description={t("adsLive.source")} /><section className="grid gap-4 rounded-2xl bg-white p-5 dark:bg-[#15172A]"><p role="status">{t("adsLive.callback." + visible)}</p><Link className="underline" href="/settings/integrations">{t("adsLive.back")}</Link></section></WorkspacePage>;
}
