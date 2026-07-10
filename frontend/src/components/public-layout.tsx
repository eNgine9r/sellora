"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import { ArrowRight, CheckCircle2, Menu, X } from "lucide-react";
import { BrandLockup } from "@/components/brand";
import { LanguageSwitcher } from "@/components/language-switcher";
import { useI18n } from "@/i18n/provider";

type PublicNavItem = { href: string; label: string };

export const publicNavItems: PublicNavItem[] = [
  { href: "#workflow", label: "landing.nav.workflow" },
  { href: "#capabilities", label: "landing.nav.capabilities" },
  { href: "#integrations", label: "landing.nav.integrations" },
];

export function PublicPageContainer({ children }: { children: ReactNode }) {
  return <div className="min-h-screen min-w-0 overflow-x-hidden bg-canvas text-text-primary">{children}</div>;
}

export function PublicSection({ id, eyebrow, title, description, children, className = "" }: { id?: string; eyebrow?: string; title?: string; description?: string; children: ReactNode; className?: string }) {
  return (
    <section id={id} className={`px-4 py-16 sm:px-6 lg:px-8 ${className}`}>
      <div className="mx-auto w-full max-w-7xl min-w-0">
        {title ? (
          <div className="mb-8 max-w-3xl">
            {eyebrow ? <p className="text-sm font-black uppercase tracking-[0.24em] text-violet-200">{eyebrow}</p> : null}
            <h2 className="mt-3 text-3xl font-black tracking-[-0.03em] text-text-primary sm:text-4xl">{title}</h2>
            {description ? <p className="mt-3 text-base leading-7 text-text-secondary">{description}</p> : null}
          </div>
        ) : null}
        {children}
      </div>
    </section>
  );
}

export function MarketingCTA({ href, children, className = "" }: { href: string; children: ReactNode; className?: string }) {
  return (
    <Link href={href} className={`inline-flex min-h-11 min-w-0 items-center justify-center gap-2 rounded-2xl bg-brand-gradient px-5 py-3 text-sm font-black text-white shadow-[var(--shadow-brand)] transition hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-canvas ${className}`}>
      <span className="truncate">{children}</span>
      <ArrowRight className="h-4 w-4 shrink-0" aria-hidden="true" />
    </Link>
  );
}

function useMobileMenu(open: boolean, onClose: () => void) {
  const panelRef = useRef<HTMLDivElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (!open) return;
    previousFocus.current = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const id = window.setTimeout(() => panelRef.current?.focus(), 0);
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = panelRef.current.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])');
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      }
      if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      window.clearTimeout(id);
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
      previousFocus.current?.focus?.();
    };
  }, [open, onClose]);
  return panelRef;
}

export function PublicHeader() {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const panelRef = useMobileMenu(open, () => setOpen(false));

  return (
    <header className="sticky top-0 z-50 border-b border-border-subtle bg-canvas/90 px-4 py-3 backdrop-blur-xl sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3">
        <Link href="/" aria-label="Sellora" className="min-w-0 rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring">
          <BrandLockup markClassName="h-9 w-9" />
        </Link>
        <nav className="hidden items-center gap-2 md:flex" aria-label={t("landing.nav.label")}>
          {publicNavItems.map((item) => <a key={item.href} href={item.href} className="rounded-2xl px-3 py-2 text-sm font-bold text-text-secondary transition hover:bg-surface-2 hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring">{t(item.label)}</a>)}
        </nav>
        <div className="hidden shrink-0 items-center gap-2 md:flex">
          <LanguageSwitcher compact />
          <Link href="/login" className="rounded-2xl border border-border-subtle bg-surface-2 px-4 py-2 text-sm font-black text-text-primary transition hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring">{t("auth.login")}</Link>
          <MarketingCTA href="/login" className="min-h-10 px-4 py-2">{t("landing.primaryCta")}</MarketingCTA>
        </div>
        <button type="button" className="grid h-11 w-11 place-items-center rounded-2xl border border-border-subtle bg-surface-2 text-text-primary transition hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring md:hidden" aria-label={t("landing.nav.mobileMenu")} aria-expanded={open} onClick={() => setOpen(true)}>
          <Menu className="h-5 w-5" aria-hidden="true" />
        </button>
      </div>
      {open ? (
        <div className="fixed inset-0 z-[var(--z-overlay)] md:hidden" role="dialog" aria-modal="true" aria-label={t("landing.nav.mobileMenu")}>
          <button className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" aria-label={t("landing.nav.closeMenu")} onClick={() => setOpen(false)} />
          <div ref={panelRef} tabIndex={-1} className="absolute right-3 top-3 w-[calc(100vw-1.5rem)] max-w-sm rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 p-4 shadow-[var(--shadow-overlay)] outline-none">
            <div className="flex items-center justify-between gap-3">
              <BrandLockup markClassName="h-9 w-9" />
              <button className="grid h-10 w-10 place-items-center rounded-2xl border border-border-subtle bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring" type="button" aria-label={t("landing.nav.closeMenu")} onClick={() => setOpen(false)}><X className="h-5 w-5" /></button>
            </div>
            <nav className="mt-5 grid gap-2" aria-label={t("landing.nav.label")}>
              {publicNavItems.map((item) => <a key={item.href} href={item.href} onClick={() => setOpen(false)} className="rounded-2xl border border-border-subtle bg-surface-2 px-4 py-3 font-bold text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring">{t(item.label)}</a>)}
            </nav>
            <div className="mt-5 grid gap-3">
              <LanguageSwitcher compact />
              <Link href="/login" className="inline-flex min-h-11 items-center justify-center rounded-2xl border border-border-subtle bg-surface-2 px-4 font-black text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring" onClick={() => setOpen(false)}>{t("auth.login")}</Link>
              <MarketingCTA href="/login" className="w-full" >{t("landing.primaryCta")}</MarketingCTA>
            </div>
          </div>
        </div>
      ) : null}
    </header>
  );
}

export function PublicFooter() {
  const { t } = useI18n();
  const legal = { privacy: t("legalLinks.privacy"), terms: t("legalLinks.terms"), dataDeletion: t("legalLinks.dataDeletion") };
  return (
    <footer className="border-t border-border-subtle bg-sidebar px-4 py-10 sm:px-6 lg:px-8">
      <div className="mx-auto grid max-w-7xl gap-8 md:grid-cols-[1fr_auto] md:items-end">
        <div className="max-w-xl">
          <BrandLockup />
          <p className="mt-4 text-sm leading-6 text-text-secondary">{t("landing.footerDescription")}</p>
        </div>
        <div className="flex flex-wrap gap-3 text-sm font-bold text-text-secondary md:justify-end">
          <Link className="rounded-xl px-2 py-1 hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring" href="/legal/privacy">{legal.privacy}</Link>
          <Link className="rounded-xl px-2 py-1 hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring" href="/legal/terms">{legal.terms}</Link>
          <Link className="rounded-xl px-2 py-1 hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring" href="/legal/data-deletion">{legal.dataDeletion}</Link>
        </div>
        <p className="text-sm text-text-muted md:col-span-2">{t("landing.footer")}</p>
      </div>
    </footer>
  );
}

export function IntegrationStatusBadge({ status }: { status: "available" | "pilot" | "beta" | "soon" | "notConnected" }) {
  const { t } = useI18n();
  const styles = {
    available: "border-success/30 bg-success/10 text-emerald-200",
    pilot: "border-warning/30 bg-warning/10 text-amber-200",
    beta: "border-info/30 bg-info/10 text-blue-200",
    soon: "border-border-subtle bg-surface-2 text-text-secondary",
    notConnected: "border-border-subtle bg-surface-2 text-text-muted",
  }[status];
  return <span className={`inline-flex min-h-7 items-center rounded-full border px-2.5 text-xs font-black ${styles}`}><CheckCircle2 className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />{t(`landing.integrationStatuses.${status}`)}</span>;
}
