"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight, KeyRound, Loader2, LogOut, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { BrandIcon } from "@/components/brand";
import { Button, Card, FormField, Input, LoadingSkeleton, StatusBadge } from "@/components/ui/primitives";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { ApiError } from "@/services/api";
import { COOKIE_SESSION_AUTH_ENABLED } from "@/services/auth.service";
import { clearPlatformMfaProof, platformAdminApi, platformMfaError } from "@/services/platform-admin";
import { PlatformDashboard } from "./platform-dashboard";
import { PlatformProblem } from "./platform-feedback";
import { PlatformMfaCode, platformMfaCodeLength } from "./platform-mfa-code";

function PlatformAccessCard({ title, description, challenge = false, children }: {
  title: string;
  description: string;
  challenge?: boolean;
  children: ReactNode;
}) {
  const Icon = challenge ? KeyRound : ShieldCheck;
  return (
    <div className="mx-auto grid max-w-md place-items-center py-6 sm:py-16">
      <Card className={`w-full border-violet-500/25 bg-[radial-gradient(ellipse_at_top_right,rgba(139,92,246,0.14),transparent_63%)] sm:p-8 ${challenge ? "shadow-[0_20px_64px_rgba(0,0,0,0.3)]" : ""}`}>
        <div className="mb-5 grid size-12 place-items-center rounded-2xl border border-violet-500/30 bg-violet-500/10 text-violet-300">
          <Icon className="size-5" aria-hidden="true" />
        </div>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{title}</h1>
        <p className="mt-2 text-sm leading-6 text-text-secondary">{description}</p>
        {children}
      </Card>
    </div>
  );
}

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
    <PlatformAccessCard title={t("platformAdmin.signInTitle")} description={t("platformAdmin.signInDescription")}>
      <form className="mt-6 grid gap-4" onSubmit={submit}>
        <FormField label={t("auth.email")}><Input name="email" type="email" autoComplete="username" required /></FormField>
        <FormField label={t("auth.password")}><Input name="password" type="password" autoComplete="current-password" required /></FormField>
        {failed ? <p role="alert" className="text-sm text-[var(--danger-foreground)]">{t("platformAdmin.signInError")}</p> : null}
        <Button variant="brand" type="submit" loading={pending}>{t("auth.login")}</Button>
      </form>
    </PlatformAccessCard>
  );
}

function PlatformMfaChallenge({ onVerified }: { onVerified: () => void }) {
  const { t } = useI18n();
  const [pending, setPending] = useState(false);
  const submitting = useRef(false);
  const [code, setCode] = useState("");
  const [error, setError] = useState<"mfaInvalid" | "mfaRateLimited" | "mfaNotEnrolled" | "mfaUnavailable">();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current || !/^[0-9]{6}$/.test(code)) return;
    submitting.current = true;
    setCode("");
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
      submitting.current = false;
      setPending(false);
    }
  }

  return (
    <PlatformAccessCard title={t("platformAdmin.mfaTitle")} description={t("platformAdmin.mfaDescription")} challenge>
      <form className="mt-7 grid gap-5" onSubmit={submit}>
        <PlatformMfaCode value={code} pending={pending} error={error ? t(`platformAdmin.${error}`) : undefined}
          onChange={(value) => { setCode(value); setError(undefined); }} />
        <Button className="justify-between rounded-xl" type="submit" aria-busy={pending}
          disabled={pending || code.length !== platformMfaCodeLength}>
          <span>{t("platformAdmin.mfaVerify")}</span>
          {pending ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : <ArrowRight className="size-4" aria-hidden="true" />}
        </Button>
        {error ? <p id="platform-mfa-error" role="alert" className="-mt-2 text-xs leading-5 text-[var(--danger-foreground)]">
          {t(`platformAdmin.${error}`)}
        </p> : null}
      </form>
    </PlatformAccessCard>
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
    content = <PlatformDashboard key={operatorId} operatorId={operatorId} recheckAccess={recheckAccess} showActivity={identity.data.capabilities.includes("activity.read")}
      showUsers={identity.data.capabilities.includes("users.read")} canArchive={identity.data.capabilities.includes("workspaces.archive")} />;
  }

  return (
    <>
      <header className="border-b border-border-subtle bg-surface-1">
        <div className="mx-auto flex min-h-16 max-w-[96rem] flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <BrandIcon priority className="size-9" />
            <div className="min-w-0">
              <p className="text-base font-bold leading-tight tracking-tight">Sellora</p>
              <p className="text-xs text-text-secondary">{t("platformAdmin.name")}</p>
            </div>
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
      <main className="mx-auto max-w-[96rem] px-4 py-4 sm:px-8 md:py-6">
        {signOutFailed ? <p className="mb-4 text-sm text-[var(--danger-foreground)]" role="alert">{t("platformAdmin.signOutError")}</p> : null}
        {content}
      </main>
    </>
  );
}
