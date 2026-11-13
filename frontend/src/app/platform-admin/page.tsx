"use client";

import { useQuery } from "@tanstack/react-query";
import { LogOut, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { BrandLockup } from "@/components/brand";
import { Button, Card, FormField, Input, LoadingSkeleton, StatusBadge } from "@/components/ui/primitives";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { ApiError } from "@/services/api";
import { COOKIE_SESSION_AUTH_ENABLED } from "@/services/auth.service";
import { clearPlatformMfaProof, platformAdminApi, platformMfaError } from "@/services/platform-admin";
import { PlatformDashboard } from "./platform-dashboard";
import { PlatformProblem } from "./platform-feedback";

function PlatformSignIn({ onSignedIn }: { onSignedIn: () => void }) {
  const { t } = useI18n();
  const { login } = useAuth();
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setPending(true);
    setFailed(false);
    try {
      await login(String(form.get("email")), String(form.get("password")));
      onSignedIn();
    } catch {
      setFailed(true);
    } finally {
      setPending(false);
    }
  }

  return (
    <Card className="mx-auto mt-12 w-full max-w-md sm:mt-20 sm:p-8">
      <ShieldCheck className="mb-4 size-6 text-violet-400" aria-hidden="true" />
      <h1 className="text-2xl font-black">{t("platformAdmin.signInTitle")}</h1>
      <p className="mt-2 text-sm leading-6 text-text-secondary">{t("platformAdmin.signInDescription")}</p>
      <form className="mt-6 grid gap-4" onSubmit={submit}>
        <FormField label={t("auth.email")}><Input name="email" type="email" autoComplete="username" required /></FormField>
        <FormField label={t("auth.password")}><Input name="password" type="password" autoComplete="current-password" required /></FormField>
        {failed ? <p role="alert" className="text-sm text-[var(--danger-foreground)]">{t("platformAdmin.signInError")}</p> : null}
        <Button variant="brand" type="submit" loading={pending}>{t("auth.login")}</Button>
      </form>
    </Card>
  );
}

function PlatformMfaChallenge({ onVerified }: { onVerified: () => void }) {
  const { t } = useI18n();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<"mfaInvalid" | "mfaRateLimited" | "mfaNotEnrolled" | "mfaUnavailable">();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    const form = event.currentTarget;
    const code = String(new FormData(form).get("code"));
    form.reset();
    setPending(true);
    setError(undefined);
    try {
      await platformAdminApi.verifyMfa(code);
      onVerified();
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401) {
        onVerified();
        return;
      }
      switch (platformMfaError(failure)) {
        case "PLATFORM_MFA_INVALID_CODE": setError("mfaInvalid"); break;
        case "PLATFORM_MFA_RATE_LIMITED": setError("mfaRateLimited"); break;
        case "PLATFORM_MFA_NOT_ENROLLED": setError("mfaNotEnrolled"); break;
        default: setError("mfaUnavailable");
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <Card className="mx-auto mt-12 w-full max-w-md sm:mt-20 sm:p-8">
      <ShieldCheck className="mb-4 size-6 text-violet-400" aria-hidden="true" />
      <h1 className="text-2xl font-black">{t("platformAdmin.mfaTitle")}</h1>
      <p className="mt-2 text-sm leading-6 text-text-secondary">{t("platformAdmin.mfaDescription")}</p>
      <form className="mt-6 grid gap-4" onSubmit={submit}>
        <FormField label={t("platformAdmin.mfaCode")}>
          <Input name="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required />
        </FormField>
        {error ? <p role="alert" className="text-sm text-[var(--danger-foreground)]">{t(`platformAdmin.${error}`)}</p> : null}
        <Button variant="brand" type="submit" loading={pending}>{t("platformAdmin.mfaVerify")}</Button>
      </form>
    </Card>
  );
}

export default function PlatformAdminPage() {
  const { t } = useI18n();
  const { currentUser, status, logout } = useAuth();
  const [signInRevision, setSignInRevision] = useState(0);
  const [isSigningOut, setIsSigningOut] = useState(false);
  const [signOutFailed, setSignOutFailed] = useState(false);
  const operatorId = currentUser?.id;
  const identity = useQuery({
    queryKey: ["platform-admin", operatorId, "identity", signInRevision],
    queryFn: ({ signal }) => platformAdminApi.identity(signal),
    enabled: status === "authenticated" && !!operatorId && COOKIE_SESSION_AUTH_ENABLED && !isSigningOut,
    retry: false,
    gcTime: 0,
  });
  useEffect(() => {
    if (status === "unauthenticated" || (identity.error instanceof ApiError && identity.error.status === 401)) {
      clearPlatformMfaProof();
    }
  }, [identity.error, status]);

  const { refetch } = identity;
  const recheckAccess = useCallback(() => { void refetch(); }, [refetch]);
  const role = identity.data?.operator_id === operatorId && !identity.error ? identity.data?.role : undefined;

  async function signOut() {
    setIsSigningOut(true);
    setSignOutFailed(false);
    try {
      await logout();
      clearPlatformMfaProof();
    } catch {
      setSignOutFailed(true);
    } finally {
      setIsSigningOut(false);
    }
  }

  let content;
  if (!COOKIE_SESSION_AUTH_ENABLED) {
    content = <PlatformProblem message="unavailable" />;
  } else if (status === "loading" || isSigningOut) {
    content = <LoadingSkeleton title={t("platformAdmin.checkingAccess")} rows={2} />;
  } else if (status === "unauthenticated" || (identity.error instanceof ApiError && identity.error.status === 401)) {
    content = <PlatformSignIn onSignedIn={() => setSignInRevision((revision) => revision + 1)} />;
  } else if (identity.isPending) {
    content = <LoadingSkeleton title={t("platformAdmin.checkingAccess")} rows={2} />;
  } else if (platformMfaError(identity.error) === "PLATFORM_MFA_REQUIRED") {
    content = <PlatformMfaChallenge onVerified={recheckAccess} />;
  } else if (identity.error) {
    const code = identity.error instanceof ApiError ? identity.error.status : 0;
    content = <PlatformProblem message={code === 403 ? "forbidden" : code === 404 ? "unavailable" : "error"} retry={code !== 403 && code !== 404 ? () => void identity.refetch() : undefined} />;
  } else if (!role || !operatorId || !identity.data?.capabilities.includes("workspaces.read")) {
    content = <PlatformProblem message="forbidden" />;
  } else {
    content = <PlatformDashboard key={operatorId} operatorId={operatorId} recheckAccess={recheckAccess} showActivity={identity.data.capabilities.includes("activity.read")} />;
  }

  return (
    <>
      <header className="border-b border-border-subtle bg-sidebar">
        <div className="mx-auto flex min-h-16 max-w-[90rem] flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <BrandLockup markClassName="h-8 w-8" />
            <span className="hidden border-l border-border-subtle pl-3 text-xs font-semibold text-text-secondary sm:inline">{t("platformAdmin.name")}</span>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            {role ? <StatusBadge>{t(`platformAdmin.roles.${role}`)}</StatusBadge> : null}
            {status === "authenticated" ? (
              <Button variant="ghost" size="sm" onClick={signOut} loading={isSigningOut}>
                <LogOut className="size-4" aria-hidden="true" />{t("actions.logout")}
              </Button>
            ) : null}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[90rem] px-4 py-6 sm:px-8 sm:py-9">
        {signOutFailed ? <p className="mb-4 text-sm text-[var(--danger-foreground)]" role="alert">{t("platformAdmin.signOutError")}</p> : null}
        {content}
      </main>
    </>
  );
}
