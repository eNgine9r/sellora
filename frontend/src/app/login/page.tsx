"use client";

import { FormEvent, useEffect, useId, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Eye, EyeOff, LockKeyhole, ShieldCheck } from "lucide-react";
import { BrandLockup } from "@/components/brand";
import { LanguageSwitcher } from "@/components/language-switcher";
import { Button, Card, FormField, Input } from "@/components/ui/primitives";
import { PublicFooter, PublicPageContainer } from "@/components/public-layout";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { AuthNetworkError, InvalidCredentialsError } from "@/services/auth.service";

type LoginIndicator = { label: string; value: string };

export default function LoginPage() {
  const router = useRouter();
  const { status, login, error: authError } = useAuth();
  const { t, tr } = useI18n();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const errorId = useId();
  const indicators = tr<LoginIndicator[]>("auth.indicators");

  useEffect(() => { if (status === "authenticated") router.replace("/dashboard"); }, [router, status]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch (exc) {
      if (exc instanceof AuthNetworkError) setError(t("auth.networkError"));
      else if (exc instanceof InvalidCredentialsError) setError(t("auth.invalidCredentials"));
      else setError(t("auth.error"));
    } finally {
      setIsSubmitting(false);
    }
  }

  const visibleError = error ?? authError;

  return (
    <PublicPageContainer>
      <main className="relative min-h-screen overflow-hidden px-4 py-5 sm:px-6 lg:px-8">
        <div className="pointer-events-none absolute left-[-12rem] top-[-12rem] h-[28rem] w-[28rem] rounded-full bg-brand-gradient opacity-20 blur-3xl" aria-hidden="true" />
        <div className="pointer-events-none absolute bottom-[-16rem] right-[-10rem] h-[30rem] w-[30rem] rounded-full bg-primary opacity-20 blur-3xl" aria-hidden="true" />
        <div className="relative z-10 mx-auto flex max-w-7xl items-center justify-between gap-3">
          <Link href="/" className="inline-flex min-h-10 items-center gap-2 rounded-2xl border border-border-subtle bg-surface-1 px-3 text-sm font-black text-text-primary transition hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"><ArrowLeft className="h-4 w-4" aria-hidden="true" />{t("auth.backHome")}</Link>
          <LanguageSwitcher compact />
        </div>

        <section className="relative z-10 mx-auto grid min-h-[calc(100vh-7rem)] max-w-7xl items-center gap-8 py-10 lg:grid-cols-[0.44fr_0.56fr]">
          <aside className="min-w-0 lg:pr-8">
            <BrandLockup />
            <h1 className="mt-8 max-w-xl text-4xl font-black leading-[1.05] tracking-[-0.04em] text-text-primary sm:text-5xl">{t("auth.contextTitle")}</h1>
            <p className="mt-5 max-w-xl text-base leading-8 text-text-secondary">{t("auth.contextDescription")}</p>
            <div className="mt-6 grid gap-3 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
              {indicators.map((indicator) => <div key={indicator.label} className="rounded-2xl border border-border-subtle bg-surface-1 p-4"><p className="text-2xl font-black text-text-primary">{indicator.value}</p><p className="mt-1 text-sm font-semibold text-text-secondary">{indicator.label}</p></div>)}
            </div>
            <div className="mt-6 flex gap-3 rounded-[var(--radius-card)] border border-border-subtle bg-surface-1 p-4 text-sm leading-6 text-text-secondary">
              <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-violet-300" aria-hidden="true" />
              <p>{t("auth.trustStatement")}</p>
            </div>
          </aside>

          <Card className="mx-auto w-full max-w-xl p-5 sm:p-8">
            <div className="grid h-12 w-12 place-items-center rounded-2xl bg-primary/15 text-violet-200"><LockKeyhole className="h-6 w-6" aria-hidden="true" /></div>
            <p className="mt-6 text-sm font-black uppercase tracking-[0.22em] text-violet-200">{t("auth.welcome")}</p>
            <h2 className="mt-3 text-3xl font-black tracking-[-0.03em] text-text-primary">{t("auth.loginTitle")}</h2>
            <p className="mt-3 text-sm leading-6 text-text-secondary">{t("auth.helper")}</p>
            <form className="mt-7 grid gap-4" onSubmit={submit} noValidate>
              <FormField label={t("auth.email")}>
                <Input type="email" autoComplete="email" inputMode="email" value={email} onChange={(event) => setEmail(event.target.value)} aria-describedby={visibleError ? errorId : undefined} aria-invalid={Boolean(visibleError)} />
              </FormField>
              <FormField label={t("auth.password")}>
                <div className="relative">
                  <Input className="pr-12" type={showPassword ? "text" : "password"} autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} aria-describedby={visibleError ? errorId : undefined} aria-invalid={Boolean(visibleError)} />
                  <button type="button" className="absolute right-1.5 top-1/2 grid h-8 w-8 -translate-y-1/2 place-items-center rounded-xl text-text-muted transition hover:bg-surface-hover hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring" aria-label={showPassword ? t("auth.hidePassword") : t("auth.showPassword")} onClick={() => setShowPassword((value) => !value)}>
                    {showPassword ? <EyeOff className="h-4 w-4" aria-hidden="true" /> : <Eye className="h-4 w-4" aria-hidden="true" />}
                  </button>
                </div>
              </FormField>
              {visibleError ? <p id={errorId} role="alert" aria-live="polite" className="rounded-2xl border border-danger/25 bg-danger/10 px-4 py-3 text-sm font-bold leading-6 text-rose-100">{visibleError}</p> : null}
              <Button className="mt-2 w-full" size="lg" variant="primary" loading={isSubmitting} type="submit">{isSubmitting ? t("auth.loading") : t("auth.login")}</Button>
            </form>
            <div className="mt-6 flex flex-wrap justify-center gap-3 text-xs font-bold text-text-muted">
              <Link className="rounded-lg px-2 py-1 hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring" href="/legal/privacy">{t("legalLinks.privacy")}</Link>
              <Link className="rounded-lg px-2 py-1 hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring" href="/legal/terms">{t("legalLinks.terms")}</Link>
              <Link className="rounded-lg px-2 py-1 hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring" href="/legal/data-deletion">{t("legalLinks.dataDeletion")}</Link>
            </div>
          </Card>
        </section>
      </main>
      <PublicFooter />
    </PublicPageContainer>
  );
}
