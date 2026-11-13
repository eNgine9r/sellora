"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { KeyRound } from "lucide-react";
import { ProviderIcon, publicAuthErrorKey, useAuthResult } from "@/app/login/auth-methods";
import { WorkspaceHeader, WorkspacePage } from "@/components/crm-workspace";
import { Button, Card, StatusBadge } from "@/components/ui/primitives";
import { useAuth } from "@/hooks/use-auth";
import { usePublicAuthOptions } from "@/hooks/use-public-auth-options";
import { useI18n } from "@/i18n/provider";
import { fetchLinkedSignInMethods, startSocialAuth, type SignInProvider } from "@/services/auth.service";

export default function SignInMethodsPage() {
  const { t, locale } = useI18n();
  const { currentUser } = useAuth();
  const { data: options } = usePublicAuthOptions();
  const result = useAuthResult();
  const [pending, setPending] = useState<SignInProvider | null>(null);
  const [error, setError] = useState<string | null>(null);
  const methods = useQuery({
    queryKey: ["linked-sign-in-methods", currentUser?.id],
    queryFn: fetchLinkedSignInMethods,
    enabled: Boolean(currentUser && options?.providers.length),
    retry: false,
  });

  async function link(provider: SignInProvider) {
    setPending(provider);
    setError(null);
    try {
      await startSocialAuth(provider, "link", locale);
    } catch (exc) {
      setError(publicAuthErrorKey(exc));
      setPending(null);
    }
  }

  return (
    <WorkspacePage>
      <WorkspaceHeader eyebrow={t("settings.label")} title={t("auth.access.methodsTitle")}
        description={t("auth.access.methodsHelp")} actions={<KeyRound className="text-primary" aria-hidden="true" />} />
      <Card className="grid gap-4">
        {!options?.providers.length ? <p className="text-sm text-text-secondary">{t("auth.access.errors.unavailable")}</p> : null}
        {error || (result && result !== "linked") ? (
          <p role="alert" className="text-sm text-danger">{t(error ?? publicAuthErrorKey(result))}</p>
        ) : null}
        {!error && result === "linked" ? <p role="status" className="text-sm text-text-secondary">{t("auth.access.linkSuccess")}</p> : null}
        {methods.isError ? (
          <div className="flex items-center gap-3">
            <p role="alert" className="text-sm text-danger">{t("auth.networkError")}</p>
            <Button type="button" variant="secondary" size="sm" onClick={() => void methods.refetch()}>{t("auth.access.retry")}</Button>
          </div>
        ) : null}
        <div className="grid gap-2 sm:grid-cols-2">
          {options?.providers.map(provider => (
            <div key={provider} className="flex items-center justify-between gap-3 rounded-xl border border-border-subtle p-3">
              <span className="inline-flex min-w-0 items-center gap-2 text-sm font-bold text-text-primary">
                <ProviderIcon provider={provider} />{provider === "google" ? "Google" : "Facebook"}
              </span>
              {methods.data?.linked.includes(provider) ? (
                <StatusBadge tone="success">{t("auth.access.linked")}</StatusBadge>
              ) : (
                <Button type="button" variant="secondary" size="sm" disabled={!methods.isSuccess || pending !== null}
                  loading={pending === provider} onClick={() => void link(provider)}>{t("auth.access.link")}</Button>
              )}
            </div>
          ))}
        </div>
      </Card>
    </WorkspacePage>
  );
}
