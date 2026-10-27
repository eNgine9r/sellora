"use client";

import Link from "next/link";
import { ReactNode, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { BarChart3, Home, LogOut, Package, Settings, ShoppingBag, Users } from "lucide-react";
import { AppSidebar } from "@/components/app-sidebar";
import { AppTopbar } from "@/components/app-topbar";
import { DesktopBrandLockup } from "@/components/brand";
import { GlobalAppLoader } from "@/components/global-app-loader";
import { DirectLiveProvider } from "@/components/direct-live-provider";
import { NoWorkspaceOnboarding } from "@/components/no-workspace-onboarding";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageSwitcher } from "@/components/language-switcher";
import { useI18n } from "@/i18n/provider";
import { useAuth } from "@/hooks/use-auth";

const protectedRoutes = [
  "/dashboard",
  "/overview",
  "/leads",
  "/direct",
  "/customers",
  "/products",
  "/inventory",
  "/orders",
  "/shipments",
  "/advertising",
  "/analytics",
  "/finance",
  "/reports",
  "/calendar",
  "/notes",
  "/insights",
  "/settings",
];

const mobileQuickNav = [
  { href: "/dashboard", labelKey: "navigation.dashboard", icon: Home },
  { href: "/leads", labelKey: "navigation.leads", icon: Users },
  { href: "/orders", labelKey: "navigation.orders", icon: ShoppingBag },
  { href: "/products", labelKey: "navigation.products", icon: Package },
  { href: "/finance", labelKey: "navigation.finance", icon: BarChart3 },
];

function isActiveNav(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

function isProtectedPath(pathname: string) {
  return protectedRoutes.some((route) => pathname === route || pathname.startsWith(`${route}/`));
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { status, currentUser, currentWorkspace, currentWorkspaceId, error, logout, switchWorkspace, reloadCurrentUser } = useAuth();
  const { t } = useI18n();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [mobileMoreOpen, setMobileMoreOpen] = useState(false);
  const protectedPath = isProtectedPath(pathname);

  useEffect(() => {
    if (protectedPath && status === "unauthenticated") router.replace("/login");
  }, [protectedPath, router, status]);

  useEffect(() => {
    if (!mobileMenuOpen) return;

    // overflow:hidden alone does not reliably lock the document on iOS Safari.
    // Freeze the document at its exact scroll position, but keep the drawer's
    // own scroll container independent and touch-scrollable.
    const scrollY = window.scrollY;
    const body = document.body;
    const html = document.documentElement;
    const previous = {
      position: body.style.position,
      top: body.style.top,
      left: body.style.left,
      right: body.style.right,
      width: body.style.width,
      overflow: body.style.overflow,
      htmlOverflow: html.style.overflow,
      htmlOverscroll: html.style.overscrollBehavior,
    };

    body.style.position = "fixed";
    body.style.top = `-${scrollY}px`;
    body.style.left = "0";
    body.style.right = "0";
    body.style.width = "100%";
    body.style.overflow = "hidden";
    html.style.overflow = "hidden";
    html.style.overscrollBehavior = "none";

    const desktop = window.matchMedia("(min-width: 1024px)");
    const closeOnDesktop = () => {
      if (desktop.matches) setMobileMenuOpen(false);
    };
    desktop.addEventListener("change", closeOnDesktop);

    return () => {
      desktop.removeEventListener("change", closeOnDesktop);
      body.style.position = previous.position;
      body.style.top = previous.top;
      body.style.left = previous.left;
      body.style.right = previous.right;
      body.style.width = previous.width;
      body.style.overflow = previous.overflow;
      html.style.overflow = previous.htmlOverflow;
      html.style.overscrollBehavior = previous.htmlOverscroll;
      window.scrollTo(0, scrollY);
    };
  }, [mobileMenuOpen]);

  useEffect(() => {
    if (!mobileMenuOpen) return;
    const onEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobileMenuOpen(false);
    };
    document.addEventListener("keydown", onEscape);
    return () => document.removeEventListener("keydown", onEscape);
  }, [mobileMenuOpen]);

  const handleLogout = async () => {
    try {
      await logout();
      setMobileMenuOpen(false);
      setMobileMoreOpen(false);
      router.replace("/login");
    } catch {
      // Do not navigate away if the server has not revoked the secure session.
    }
  };

  if (!protectedPath) return <>{children}</>;
  if (status === "loading") return <GlobalAppLoader />;
  if (status === "unauthenticated") return <div className="grid min-h-screen place-items-center bg-canvas text-text-secondary">{t("common.redirectingLogin")}</div>;

  const profileInitial = ([currentUser?.first_name, currentUser?.last_name].filter(Boolean).join(" ") || currentUser?.email || "S").slice(0, 1).toUpperCase();

  return (
    <DirectLiveProvider workspaceId={currentWorkspaceId}>
      <div className="min-h-screen w-full overflow-x-clip bg-canvas text-text-primary lg:grid lg:[--sidebar-width:232px] 2xl:[--sidebar-width:244px] lg:[--topbar-height:72px] lg:[grid-template-columns:var(--sidebar-width)_minmax(0,1fr)] lg:[grid-template-rows:var(--topbar-height)_minmax(0,1fr)]" data-protected-shell-grid>
        <div className="relative hidden min-w-0 overflow-hidden border-b border-r border-border-subtle bg-sidebar px-5 lg:flex lg:h-[var(--topbar-height)] lg:w-[var(--sidebar-width)] lg:items-center 2xl:px-6" data-shell-brand-cell>
          <div className="pointer-events-none absolute -left-14 -top-16 h-32 w-32 rounded-full bg-primary/[0.10] blur-3xl" aria-hidden="true" />
          <Link href="/dashboard" aria-label={t("navigation.dashboard")} className="group relative flex w-full min-w-0 items-center rounded-xl py-1 transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring">
            <DesktopBrandLockup />
          </Link>
        </div>
        <aside className="hidden min-h-0 lg:block lg:[grid-column:1] lg:[grid-row:2]">
          <AppSidebar showBrand={false} />
        </aside>
        <div className="min-w-0 overflow-x-clip pb-[calc(5.5rem+env(safe-area-inset-bottom))] lg:pb-0 lg:[grid-column:2] lg:[grid-row:1/3] lg:grid lg:min-h-0 lg:[grid-template-rows:var(--topbar-height)_minmax(0,1fr)]" data-shell-page-column>
          <AppTopbar
            currentUser={currentUser}
            currentWorkspace={currentWorkspace}
            currentWorkspaceId={currentWorkspaceId}
            mobileMoreOpen={mobileMoreOpen}
            onOpenMenu={() => { setMobileMoreOpen(false); setMobileMenuOpen(true); }}
            onCloseMobileMore={() => setMobileMoreOpen(false)}
            onLogout={handleLogout}
            onSwitchWorkspace={switchWorkspace}
            onWorkspaceCreated={reloadCurrentUser}
          />
          <div className="min-w-0 overflow-x-clip lg:min-h-0 lg:overflow-y-auto">
            {error ? <p className="mx-4 mt-3 rounded-2xl border border-amber-400/20 bg-amber-400/10 px-4 py-3 text-sm font-semibold text-warning md:mx-6">{error}</p> : null}
            {!currentWorkspaceId ? <NoWorkspaceOnboarding onWorkspaceCreated={reloadCurrentUser} onSwitchWorkspace={switchWorkspace} /> : children}
          </div>
        </div>

        <nav className="mobile-bottom-nav fixed inset-x-3 bottom-[max(0.5rem,env(safe-area-inset-bottom))] z-40 mx-auto max-w-md rounded-[24px] border border-border-subtle bg-surface-1/95 p-1 shadow-[0_10px_34px_rgba(0,0,0,0.28)] backdrop-blur-lg lg:hidden" aria-label={t("mobileNavigation.bottomNav")}>
          <div className="grid grid-cols-6 gap-0.5">
            {mobileQuickNav.map((item) => {
              const Icon = item.icon;
              const active = isActiveNav(pathname, item.href);
              return <Link key={item.href} href={item.href} className={`flex min-h-[3.375rem] min-w-0 flex-col items-center justify-center rounded-[18px] px-0.5 py-1 text-[10px] font-semibold leading-tight transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring ${active ? "bg-primary/10 text-primary" : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"}`} aria-current={active ? "page" : undefined}><Icon className="h-[18px] w-[18px]" aria-hidden="true" /><span className="mt-1 block w-full truncate text-center">{item.href === "/orders" ? t("mobileNavigation.ordersShort") : t(item.labelKey)}</span></Link>;
            })}
            <button type="button" className={`flex min-h-[3.375rem] min-w-0 items-center justify-center rounded-[18px] px-0.5 py-1 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring ${mobileMoreOpen ? "bg-surface-selected text-primary" : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"}`} aria-label={t("accountMenu.profile")} aria-haspopup="dialog" aria-expanded={mobileMoreOpen} onClick={() => setMobileMoreOpen(true)}>
              <span className="grid h-8 w-8 place-items-center rounded-full border border-primary/25 bg-primary/15 text-xs font-bold text-primary">{profileInitial}</span>
            </button>
          </div>
        </nav>

        {mobileMenuOpen ? (
          <div className="mobile-sidebar-drawer fixed inset-0 z-[80] h-[100dvh] overscroll-none lg:hidden" role="dialog" aria-modal="true" aria-label={t("mobileNavigation.drawer")}>
            <button type="button" className="absolute inset-0 touch-none bg-[var(--overlay-background)] backdrop-blur-sm" aria-label={t("actions.close")} onClick={() => setMobileMenuOpen(false)} />
            <div className="relative grid h-[100dvh] w-[88vw] max-w-sm grid-rows-[minmax(0,1fr)_auto] overflow-hidden bg-sidebar shadow-2xl">
              <AppSidebar onNavigate={() => setMobileMenuOpen(false)} />
              <div className="mobile-sidebar-footer-compact min-w-0 border-t border-border-subtle bg-sidebar px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-2">
                <div className="mb-2 flex min-w-0 items-center gap-2.5 rounded-xl border border-border-subtle bg-surface-1/70 px-3 py-2">
                  <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-primary/15 text-xs font-bold text-primary" aria-hidden="true">{(currentWorkspace?.workspace_name ?? "S").slice(0, 1)}</div>
                  <div className="min-w-0 flex-1 leading-tight" aria-label={t("mobileSidebar.profile")}>
                    <p className="truncate text-xs font-semibold text-text-primary">{currentWorkspace?.workspace_name ?? t("accountMenu.workspace")}</p>
                    <p className="mt-0.5 truncate text-[11px] text-text-muted">{currentUser?.email}</p>
                  </div>
                </div>
                <div className="flex min-w-0 items-center justify-between gap-1.5 [&>button]:!h-11 [&>button]:!min-h-11 [&>label]:!h-11 [&>label]:!min-h-11" aria-label={t("mobileSidebar.quickControls")}>
                  <Link href="/settings" onClick={() => setMobileMenuOpen(false)} aria-label={t("navigation.settings")} title={t("navigation.settings")} className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-border-subtle bg-surface-2 text-text-secondary transition hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring">
                    <Settings className="h-[18px] w-[18px]" aria-hidden="true" />
                  </Link>
                  <LanguageSwitcher compact />
                  <ThemeToggle compact />
                  <button type="button" className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-border-subtle bg-surface-2 text-text-secondary transition hover:border-danger/30 hover:bg-[var(--danger-surface)] hover:text-danger focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring" aria-label={t("actions.logout")} title={t("actions.logout")} onClick={handleLogout}>
                    <LogOut className="h-[18px] w-[18px]" aria-hidden="true" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </DirectLiveProvider>
  );
}

// Mobile UI contract: floating-capsule five-primary-links profile-sheet subtle-active-state.
