"use client";

import { FormEvent, useEffect, useId, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Eye, EyeOff, LockKeyhole, ShieldCheck } from "lucide-react";
import { BrandLockup } from "@/components/brand";
import { LanguageSwitcher } from "@/components/language-switcher";
import { Button, FormField, Input } from "@/components/ui/primitives";
import { PublicFooter } from "@/components/public-layout";
import { useAuth } from "@/hooks/use-auth";
import { useI18n } from "@/i18n/provider";
import { AuthNetworkError, InvalidCredentialsError } from "@/services/auth.service";

import { CrmPreview } from "@/components/crm-preview";
import styles from "./login.module.css";

export default function LoginPage() {
  const router = useRouter();
  const { status, login, error: authError } = useAuth();
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const errorId = useId();

  useEffect(() => { if (status === "authenticated") router.replace("/dashboard"); }, [router, status]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) return;
    if (!event.currentTarget.checkValidity()) {
      setError("auth.validationError");
      event.currentTarget.querySelector<HTMLInputElement>("input:invalid")?.focus();
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch (exc) {
      if (exc instanceof AuthNetworkError) setError("auth.networkError");
      else if (exc instanceof InvalidCredentialsError) setError("auth.invalidCredentials");
      else setError("auth.error");
    } finally {
      setIsSubmitting(false);
    }
  }

  const visibleError = error ? t(error) : authError;

  return (
    <div className={styles.page}>
      <header className={styles.topbar}>
        <Link href="/" aria-label="Sellora"><BrandLockup markClassName="h-8 w-8" /></Link>
        <div className={styles.topActions}><Link href="/" className={styles.back} aria-label={t("auth.backHome")}><ArrowLeft size={15} aria-hidden="true"/><span>{t("auth.backHome")}</span></Link><LanguageSwitcher compact /></div>
      </header>
      <main className={styles.main}>
        <aside className={styles.context}>
          <p className={styles.eyebrow}>{t("auth.workspaceLabel")}</p>
          <h2>{t("auth.contextTitle")}</h2>
          <p>{t("auth.contextDescription")}</p>
          <div className={styles.preview}><CrmPreview compact /></div>
          <div className={styles.previewLabel}><span>Sellora / CRM</span><span>{t("auth.previewLabel")}</span></div>
        </aside>
        <section className={styles.formCard} aria-labelledby="login-title">
          <div className={styles.formSymbol}><LockKeyhole size={22} aria-hidden="true"/></div>
          <p className={styles.welcome}>{t("auth.welcome")}</p>
          <h1 id="login-title">{t("auth.loginTitle")}</h1>
          <p className={styles.helper}>{t("auth.helper")}</p>
          <form className={styles.form} onSubmit={submit} noValidate aria-busy={isSubmitting}>
            <FormField label={t("auth.email")}>
              <Input required name="email" type="email" autoComplete="email" inputMode="email" autoCapitalize="none" spellCheck={false} value={email} onChange={event => setEmail(event.target.value)} aria-describedby={visibleError ? errorId : undefined} aria-invalid={Boolean(visibleError)} />
            </FormField>
            <FormField label={t("auth.password")}>
              <div className={styles.passwordField}>
                <Input required aria-label={t("auth.password")} name="password" type={showPassword ? "text" : "password"} autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} aria-describedby={visibleError ? errorId : undefined} aria-invalid={Boolean(visibleError)} />
                <button type="button" className={styles.showPassword} aria-label={showPassword ? t("auth.hidePassword") : t("auth.showPassword")} aria-pressed={showPassword} onClick={() => setShowPassword(value => !value)}>{showPassword ? <EyeOff size={18} aria-hidden="true"/> : <Eye size={18} aria-hidden="true"/>}</button>
              </div>
            </FormField>
            {visibleError ? <p id={errorId} role="alert" className={styles.error}>{visibleError}</p> : null}
            <Button className={styles.submit} loading={isSubmitting} type="submit">{isSubmitting ? t("auth.loading") : t("auth.login")}<ArrowRight size={17} aria-hidden="true"/></Button>
          </form>
          <p className={styles.formNote}>{t("auth.formNote")}</p>
          <div className={styles.trust}><ShieldCheck size={17} aria-hidden="true"/><p>{t("auth.trustStatement")}</p></div>
          <div className={styles.legal}>
            <Link href="/legal/privacy">{t("legalLinks.privacy")}</Link>
            <Link href="/legal/terms">{t("legalLinks.terms")}</Link>
            <Link href="/legal/data-deletion">{t("legalLinks.dataDeletion")}</Link>
          </div>
        </section>
      </main>
      <PublicFooter />
    </div>
  );
}
