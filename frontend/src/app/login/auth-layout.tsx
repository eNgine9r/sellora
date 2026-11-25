"use client";

import Link from "next/link";
import { type ReactNode } from "react";
import { ArrowLeft } from "lucide-react";
import { BrandLockup } from "@/components/brand";
import { CrmPreview } from "@/components/crm-preview";
import { LanguageSwitcher } from "@/components/language-switcher";
import { PublicFooter } from "@/components/public-layout";
import { useI18n } from "@/i18n/provider";
import styles from "./login.module.css";

export function AuthLayout({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  return (
    <div className={styles.page}>
      <header className={styles.topbar}>
        <Link href="/" aria-label="Sellora"><BrandLockup markClassName="h-8 w-8" /></Link>
        <div className={styles.topActions}>
          <Link href="/" className={styles.back} aria-label={t("auth.backHome")}>
            <ArrowLeft size={16} aria-hidden="true" /><span>{t("auth.backHome")}</span>
          </Link>
          <LanguageSwitcher compact />
        </div>
      </header>
      <main className={styles.main}>
        <aside className={styles.context}>
          <h2>{t("auth.contextTitle")}</h2>
          <p>{t("auth.contextDescription")}</p>
          <div className={styles.preview}><CrmPreview compact /></div>
        </aside>
        <section className={styles.formCard} aria-labelledby="auth-title">
          {children}
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
