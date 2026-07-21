"use client";

import Link from "next/link";
import { ReactNode, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { BarChart3, Home, Package, ShoppingBag, Users } from "lucide-react";
import { AppSidebar } from "@/components/app-sidebar";
import { AppTopbar } from "@/components/app-topbar";
import { BrandLockup } from "@/components/brand";
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
    document.body.classList.toggle("overflow-hidden", mobileMenuOpen);
    return () => document.body.classList.remove("overflow-hidden");
  }, [mobileMenuOpen]);

  const handleLogout = () => {
    logout();
    router.replace("/login");
  };

  if (!protectedPath) return <>{children}</>;
  if (status === "loading") return <div className="grid min-h-screen place-items-center bg-canvas text-text-secondary">{t("common.loadingSellora")}</div>;
  if (status === "unauthenticated") return <div className="grid min-h-screen place-items-center bg-canvas text-text-secondary">{t("common.redirectingLogin")}</div>;

  const profileInitial = ([currentUser?.first_name, currentUser?.last_name].filter(Boolean).join(" ") || currentUser?.email || "S").slice(0, 1).toUpperCase();

  return (
    <DirectLiveProvider workspaceId={currentWorkspaceId}>
      <div className="min-h-screen w-full overflow-x-hidden bg-canvas text-text-primary lg:grid lg:[--sidebar-width:220px] lg:[--topbar-height:72px] lg:[grid-template-columns:var(--sidebar-width)_minmax(0,1fr)] lg:[grid-template-rows:var(--topbar-height)_minmax(0,1fr)]" data-protected-shell-grid>
        <div className="hidden min-w-0 border-b border-r border-border-subtle bg-canvas/92 px-4 backdrop-blur-xl lg:flex lg:h-[var(--topbar-height)] lg:w-[var(--sidebar-width)] lg:items-center" data-shell-brand-cell>
          <Link href="/dashboard" aria-label={t("navigation.dashboard")} className="flex min-w-0 items-center rounded-2xl border border-transparent px-1 py-1 transition hover:border-border-subtle hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring">
            <BrandLockup markClassName="h-10 w-10" textClassName="text-text-primary" />
          </Link>
        </div>
        <aside className="hidden min-h-0 lg:block lg:[grid-column:1] lg:[grid-row:2]">
          <AppSidebar showBrand={false} />
        </aside>
        <div className="min-w-0 overflow-x-hidden pb-28 lg:pb-0 lg:[grid-column:2] lg:[grid-row:1/3] lg:grid lg:min-h-0 lg:[grid-template-rows:var(--topbar-height)_minmax(0,1fr)]">
          <AppTopbar
            currentUser={currentUser}
            currentWorkspace={currentWorkspace}
            currentWorkspaceId={currentWorkspaceId}
            mobileMoreOpen={mobileMoreOpen}
            onOpenMenu={() => setMobileMenuOpen(true)}
            onOpenMobileMore={() => setMobileMoreOpen(true)}
            onCloseMobileMore={() => setMobileMoreOpen(false)}
            onLogout={handleLogout}
            onSwitchWorkspace={switchWorkspace}
            onWorkspaceCreated={reloadCurrentUser}
          />
          <div className="min-w-0 overflow-x-hidden lg:min-h-0 lg:overflow-y-auto">
            {error ? <p className="mx-4 mt-3 rounded-2xl border border-amber-400/20 bg-amber-400/10 px-4 py-3 text-sm font-semibold text-warning md:mx-6">{error}</p> : null}
            {!currentWorkspaceId ? <NoWorkspaceOnboarding onWorkspaceCreated={reloadCurrentUser} onSwitchWorkspace={switchWorkspace} /> : children}
          </div>
        </div>

        <nav className="mobile-bottom-nav fixed inset-x-3 bottom-[max(0.75rem,env(safe-area-inset-bottom))] z-40 mx-auto max-w-md rounded-[28px] border border-border-subtle bg-surface-1/90 p-1.5 shadow-[0_18px_55px_rgba(0,0,0,0.38)] backdrop-blur-xl lg:hidden" aria-label={t("mobileNavigation.bottomNav")}>
          <div className="grid grid-cols-6 gap-1">
            {mobileQuickNav.map((item) => {
              const Icon = item.icon;
              const active = isActiveNav(pathname, item.href);
              return <Link key={item.href} href={item.href} className={`grid min-h-[3.75rem] min-w-0 place-items-center rounded-2xl px-1 py-1 text-[0.64rem] font-black transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring ${active ? "bg-surface-selected text-primary" : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"}`} aria-current={active ? "page" : undefined}><Icon className="h-4 w-4" aria-hidden="true" /><span className="mt-0.5 max-w-full truncate">{t(item.labelKey)}</span></Link>;
            })}
            <button type="button" className={`grid min-h-[3.75rem] min-w-0 place-items-center rounded-2xl px-1 py-1 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring ${mobileMoreOpen ? "bg-surface-selected text-primary" : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"}`} aria-label={t("accountMenu.profile")} aria-expanded={mobileMoreOpen} onClick={() => setMobileMoreOpen(true)}>
              <span className="grid h-8 w-8 place-items-center rounded-full border border-primary/25 bg-primary/15 text-xs font-black text-primary">{profileInitial}</span>
            </button>
          </div>
        </nav>

        {mobileMenuOpen ? (
          <div className="mobile-sidebar-drawer fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label={t("mobileNavigation.drawer")}>
            <button className="absolute inset-0 bg-[var(--overlay-background)] backdrop-blur-sm" aria-label={t("actions.close")} onClick={() => setMobileMenuOpen(false)} />
            <div className="relative h-full w-[88vw] max-w-sm overflow-hidden bg-sidebar shadow-2xl">
              <AppSidebar onNavigate={() => setMobileMenuOpen(false)} />
              <div className="mobile-sidebar-footer-compact absolute inset-x-0 bottom-0 border-t border-border-subtle bg-sidebar p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
                <div className="mb-2 flex min-w-0 items-center gap-3 rounded-2xl bg-surface-1 p-3 text-sm text-text-secondary">
                  <div className="grid h-9 w-9 shrink-0 place-items-center rounded-2xl bg-primary/15 text-xs font-black text-primary">{(currentWorkspace?.workspace_name ?? "S").slice(0, 1)}</div>
                  <div className="min-w-0 leading-tight" aria-label={t("mobileSidebar.profile")}><p className="truncate font-black">{currentWorkspace?.workspace_name ?? "Workspace"}</p><p className="truncate text-xs text-text-muted">{currentUser?.email}</p></div>
                </div>
                <div className="grid grid-cols-2 gap-2" aria-label={t("mobileSidebar.quickControls")}><LanguageSwitcher compact /><ThemeToggle compact /></div>
                <button className="mt-2 min-h-11 w-full rounded-2xl border border-border-subtle bg-surface-2 px-3 text-sm font-bold text-text-primary transition hover:bg-surface-hover" onClick={handleLogout}>{t("actions.logout")}</button>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </DirectLiveProvider>
  );
}

// Mobile UI contract: floating-capsule five-primary-links profile-sheet subtle-active-state.
