"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Button, WorkspaceHeader, WorkspacePage } from "@/components/crm-workspace";
import { LoadingSkeleton } from "@/components/ui/states";
import { useI18n } from "@/i18n/provider";

const safeStatuses = new Set(["success", "permission_missing", "profile_failed", "account_not_professional", "account_type_unverified", "permission_failed", "invalid_state", "failed", "processing"]);

export default function InstagramCallbackPage() {
  const { t } = useI18n();
  const router = useRouter();
  const params = useSearchParams();
  const [seconds, setSeconds] = useState(3);
  const status = useMemo(() => {
    const raw = params.get("status") ?? "processing";
    return safeStatuses.has(raw) ? raw : "failed";
  }, [params]);
  useEffect(() => {
    window.history.replaceState(null, "", `/settings/integrations/instagram/callback?status=${status}`);
  }, [status]);
  useEffect(() => { const id = window.setInterval(() => setSeconds((value) => Math.max(0, value - 1)), 1000); return () => window.clearInterval(id); }, []);
  useEffect(() => { if (seconds === 0) router.replace("/settings/integrations/instagram"); }, [router, seconds]);
  const success = status === "success";
  return (
    <WorkspacePage>
      <WorkspaceHeader eyebrow="Meta Instagram" title={t("instagramSettings.callback.title")} description={t("instagramSettings.callback.description")} />
      {status === "processing" ? <LoadingSkeleton /> : null}
      <section className="rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-5 shadow-[var(--shadow-card)]">
        <h2 className="text-xl font-black text-text-primary">{t(success ? "instagramSettings.callback.success" : `instagramSettings.callback.status.${status}`)}</h2>
        <p className="mt-2 text-sm leading-6 text-text-secondary">{t("instagramSettings.callback.redirect", { seconds })}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button onClick={() => router.replace("/settings/integrations/instagram")}>{t("instagramSettings.openSettings")}</Button>
          {!success ? <Link className="inline-flex min-h-10 items-center rounded-2xl border border-border-subtle bg-surface-2 px-4 text-sm font-black text-text-primary" href="/settings/integrations">{t("instagramSettings.backToIntegrations")}</Link> : null}
        </div>
      </section>
    </WorkspacePage>
  );
}
