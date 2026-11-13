"use client";

import { type FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Eye, EyeOff, Mail } from "lucide-react";
import { AuthLayout } from "@/app/login/auth-layout";
import { ProviderButtons, publicAuthErrorKey, useAuthResult } from "@/app/login/auth-methods";
import styles from "@/app/login/login.module.css";
import { Button, FormField, Input } from "@/components/ui/primitives";
import { useAuth } from "@/hooks/use-auth";
import { usePublicAuthOptions } from "@/hooks/use-public-auth-options";
import { useI18n } from "@/i18n/provider";
import { confirmRegistration, sendRegistrationCode, startSocialAuth, type SignInProvider } from "@/services/auth.service";

export default function RegisterPage() {
  const router = useRouter();
  const { status } = useAuth();
  const { t, locale } = useI18n();
  const options = usePublicAuthOptions();
  const authResult = useAuthResult();
  const socialVerification = authResult === "verify_email";
  const [emailMode, setEmailMode] = useState(false);
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [retryAt, setRetryAt] = useState(0);
  const [accepted, setAccepted] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [providerPending, setProviderPending] = useState<SignInProvider | null>(null);
  const [pending, setPending] = useState<"send" | "verify" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const busy = pending !== null || providerPending !== null || status === "loading";
  const providers = options.data?.signup_providers ?? [];
  const emailAvailable = options.data?.email_registration ?? false;
  const showEmail = emailAvailable && (socialVerification || emailMode || providers.length === 0);

  useEffect(() => {
    if (status === "authenticated") router.replace("/dashboard");
  }, [router, status]);

  useEffect(() => {
    if (retryAt) {
      const timer = window.setTimeout(() => setRetryAt(0), Math.max(0, retryAt - Date.now()));
      return () => window.clearTimeout(timer);
    }
  }, [retryAt]);

  async function choose(provider: SignInProvider) {
    if (busy) return;
    if (!accepted) {
      setError("auth.access.acceptRequired");
      document.getElementById("signup-terms")?.focus();
      return;
    }
    setError(null);
    setProviderPending(provider);
    try {
      await startSocialAuth(provider, "register", locale, true);
    } catch (exc) {
      setError(publicAuthErrorKey(exc));
      setProviderPending(null);
    }
  }

  async function send() {
    if (busy || retryAt) return;
    if (!socialVerification && !accepted) {
      setError("auth.access.acceptRequired");
      document.getElementById("signup-terms")?.focus();
      return;
    }
    setPending("send");
    setError(null);
    try {
      const address = email.trim();
      await sendRegistrationCode(address, locale, socialVerification);
      setEmail(address);
      setSent(true);
      setRetryAt(Date.now() + 60_000);
    } catch (exc) {
      setError(publicAuthErrorKey(exc));
    } finally {
      setPending(null);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    if (!sent) {
      await send();
      return;
    }
    const fields = new FormData(event.currentTarget);
    setError(null);
    setPending("verify");
    try {
      await confirmRegistration({
        email, locale, code: String(fields.get("code") ?? ""), social: socialVerification,
        first_name: String(fields.get("first_name") ?? ""), password: socialVerification ? undefined : String(fields.get("password") ?? ""),
        accepts_terms: accepted,
      });
      window.location.replace(new URL("/dashboard", window.location.origin).href);
      return;
    } catch (exc) {
      setError(publicAuthErrorKey(exc));
    } finally {
      setPending(null);
    }
  }

  const callbackError = authResult && !socialVerification ? publicAuthErrorKey(authResult) : null;
  const visibleError = error ?? callbackError;
  const unavailable = options.isSuccess && !providers.length && !emailAvailable;
  const title = socialVerification ? "verifyTitle" : "createAccount";

  return (
    <AuthLayout>
      <h1 id="auth-title">{t(`auth.access.${title}`)}</h1>
      <p className={styles.helper}>{t(socialVerification ? "auth.access.verifyHelp" : "auth.access.signupHelp")}</p>
      {visibleError && !showEmail ? <p className={styles.error} role="alert">{t(visibleError)}</p> : null}
      {options.isPending ? <p className={styles.formNote} role="status">{t("auth.access.loadingOptions")}</p> : null}
      {options.isError || unavailable ? (
        <p className={styles.error} role="status">{t(options.isError ? "auth.networkError" : "auth.access.errors.registration_unavailable")}</p>
      ) : null}
      {!socialVerification && !unavailable && options.isSuccess ? (
        <label className={styles.consent}>
          <input id="signup-terms" type="checkbox" checked={accepted} disabled={busy} onChange={event => {
            setAccepted(event.target.checked);
            if (error === "auth.access.acceptRequired") setError(null);
          }} />
          <span>{t("auth.access.consent")} <Link href="/legal/terms" target="_blank" rel="noreferrer">{t("auth.access.consentTerms")}</Link> {t("auth.access.consentAnd")} <Link href="/legal/privacy" target="_blank" rel="noreferrer">{t("auth.access.consentPrivacy")}</Link>.</span>
        </label>
      ) : null}
      {!socialVerification && !emailMode && providers.length ? (
        <ProviderButtons providers={providers} pending={providerPending} disabled={busy} onChoose={choose} />
      ) : null}
      {!showEmail && emailAvailable ? (
        <>
          <div className={styles.divider}>{t("auth.access.orEmail")}</div>
          <button type="button" className={styles.secondaryAction} disabled={busy} onClick={() => setEmailMode(true)}>
            <Mail size={17} aria-hidden="true" />{t("auth.access.continueEmail")}
          </button>
        </>
      ) : null}
      {showEmail ? (
        <form className={styles.form} onSubmit={submit} aria-busy={busy}>
          <FormField label={t("auth.email")}>
            <Input type="email" name="email" required maxLength={255} inputMode="email" autoComplete="email" value={email}
              readOnly={sent || busy} onChange={event => setEmail(event.target.value)} />
          </FormField>
          {sent ? (
            <>
              <div className={styles.codePanel}>
                <p role="status">{t("auth.access.codeSent")}</p>
                <FormField label={t("auth.access.emailCode")}>
                  <Input className={styles.code} name="code" inputMode="numeric" autoComplete="one-time-code" required
                    pattern="[0-9]{6}" minLength={6} maxLength={6} placeholder="000000"
                    onChange={event => { event.target.value = event.target.value.replace(/\D/g, ""); }} />
                </FormField>
                <div className={styles.codeActions}>
                  <button type="button" disabled={busy || Boolean(retryAt)} onClick={send}>{t(retryAt ? "auth.access.resendWait" : "auth.access.resend")}</button>
                  <button type="button" disabled={busy} onClick={() => { setSent(false); setRetryAt(0); setError(null); }}>{t("auth.access.changeEmail")}</button>
                </div>
              </div>
              {!socialVerification ? (
                <>
                  <FormField label={t("auth.access.firstName")}>
                    <Input name="first_name" autoComplete="given-name" maxLength={100} required />
                  </FormField>
                  <FormField label={t("auth.password")} hint={t("auth.access.passwordHint")}>
                    <div className={styles.passwordField}>
                      <Input name="password" aria-label={t("auth.password")} type={showPassword ? "text" : "password"}
                        autoComplete="new-password" minLength={12} maxLength={128} required />
                      <button type="button" className={styles.showPassword} aria-label={t(showPassword ? "auth.hidePassword" : "auth.showPassword")}
                        aria-pressed={showPassword} onClick={() => setShowPassword(value => !value)}>
                        {showPassword ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
                      </button>
                    </div>
                  </FormField>
                </>
              ) : null}
            </>
          ) : null}
          <Button className={styles.submit} type="submit" loading={pending !== null} disabled={busy || (sent && !socialVerification && !accepted)}>
            {t(sent ? socialVerification ? "auth.access.verifyAction" : "auth.access.createAccount" : "auth.access.sendCode")}
            <ArrowRight size={17} aria-hidden="true" />
          </Button>
          <div className={styles.formFeedback}>
            {visibleError ? <p className={styles.error} role="alert">{t(visibleError)}</p> : null}
          </div>
          {emailMode && providers.length ? (
            <button type="button" className={styles.secondaryAction} disabled={busy} onClick={() => {
              setEmailMode(false); setSent(false); setRetryAt(0); setError(null);
            }}>{t("auth.access.otherMethods")}</button>
          ) : null}
        </form>
      ) : null}
      <p className={styles.formNote}>{t("auth.access.haveAccount")} <Link href="/login">{t("auth.login")}</Link></p>
    </AuthLayout>
  );
}
