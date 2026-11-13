"use client";

import { FormEvent, useEffect, useId, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Eye, EyeOff } from "lucide-react";
import { Button, FormField, Input } from "@/components/ui/primitives";
import { useAuth } from "@/hooks/use-auth";
import { usePublicAuthOptions } from "@/hooks/use-public-auth-options";
import { useI18n } from "@/i18n/provider";
import { AuthNetworkError, AuthRateLimitedError, InvalidCredentialsError, startSocialAuth, type SignInProvider } from "@/services/auth.service";

import { AuthLayout } from "./auth-layout";
import { ProviderButtons, publicAuthErrorKey, useAuthResult } from "./auth-methods";
import styles from "./login.module.css";

export default function LoginPage() {
  const router = useRouter();
  const { status, login, error: authError } = useAuth();
  const { t, locale } = useI18n();
  const { data: options } = usePublicAuthOptions();
  const authResult = useAuthResult();
  const [providerPending, setProviderPending] = useState<SignInProvider | null>(null);
  const canRegister = Boolean(options?.email_registration || options?.signup_providers.length);
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const errorId = useId();

  useEffect(() => { if (status === "authenticated") router.replace("/dashboard"); }, [router, status]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) return;
    if (providerPending) return;
    // The browser can accept typing before React hydration. Controlled inputs
    // could then display valid DOM values while stale React state submits "".
    // Read the submitted DOM form itself; leave credential fields uncontrolled
    // so hydration does not clobber early typing or password-manager autofill.
    const form = event.currentTarget;
    if (!form.checkValidity()) {
      setError("auth.validationError");
      form.querySelector<HTMLInputElement>("input:invalid")?.focus();
      return;
    }
    const data = new FormData(form);
    const email = String(data.get("email") ?? "").trim();
    const password = String(data.get("password") ?? "");
    if (!email || !password) {
      setError("auth.validationError");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch (exc) {
      if (exc instanceof AuthNetworkError) setError("auth.networkError");
      else if (exc instanceof AuthRateLimitedError) setError("auth.access.rateLimited");
      else if (exc instanceof InvalidCredentialsError) setError("auth.invalidCredentials");
      else setError("auth.error");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function choose(provider: SignInProvider) {
    if (providerPending || isSubmitting) return;
    setError(null);
    setProviderPending(provider);
    try {
      await startSocialAuth(provider, "login", locale);
    } catch (exc) {
      setError(publicAuthErrorKey(exc));
      setProviderPending(null);
    }
  }

  const visibleError = error ? t(error) : authError;
  const socialError = authResult && !error ? t(publicAuthErrorKey(authResult)) : null;

  return (
    <AuthLayout>
      <h1 id="auth-title">{t("auth.loginTitle")}</h1>
      <p className={styles.helper}>{t("auth.helper")}</p>
      {socialError ? <p role="alert" className={styles.error}>{socialError}</p> : null}
      {options?.providers.length ? (
        <>
          <ProviderButtons providers={options.providers} pending={providerPending} disabled={isSubmitting} onChoose={choose} />
          <div className={styles.divider}>{t("auth.access.orEmail")}</div>
        </>
      ) : null}
      <form className={styles.form} onSubmit={submit} noValidate aria-busy={isSubmitting}>
        <FormField label={t("auth.email")}>
          <Input required name="email" type="email" autoComplete="email" inputMode="email" autoCapitalize="none" spellCheck={false} aria-describedby={visibleError ? errorId : undefined} aria-invalid={Boolean(visibleError)} />
        </FormField>
        <FormField label={t("auth.password")}>
          <div className={styles.passwordField}>
            <Input required aria-label={t("auth.password")} name="password" type={showPassword ? "text" : "password"} autoComplete="current-password" aria-describedby={visibleError ? errorId : undefined} aria-invalid={Boolean(visibleError)} />
            <button type="button" className={styles.showPassword} aria-label={showPassword ? t("auth.hidePassword") : t("auth.showPassword")} aria-pressed={showPassword} onClick={() => setShowPassword(value => !value)}>{showPassword ? <EyeOff size={18} aria-hidden="true"/> : <Eye size={18} aria-hidden="true"/>}</button>
          </div>
        </FormField>
        {visibleError ? <p id={errorId} role="alert" className={styles.error}>{visibleError}</p> : null}
        <Button className={styles.submit} loading={isSubmitting} disabled={providerPending !== null} type="submit">{isSubmitting ? t("auth.loading") : t("auth.login")}<ArrowRight size={17} aria-hidden="true"/></Button>
      </form>
      {canRegister ? (
        <p className={styles.formNote}>{t("auth.access.noAccount")} <Link href="/register">{t("auth.access.createAccount")}</Link></p>
      ) : null}
    </AuthLayout>
  );
}
