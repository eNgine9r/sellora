"use client";

import Link from "next/link";
import { ReactNode, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { BarChart3, Home, MoreHorizontal, Package, ShoppingBag, Users } from "lucide-react";
import { AppSidebar } from "@/components/app-sidebar";
import { AppTopbar } from "@/components/app-topbar";
import { NoWorkspaceOnboarding } from "@/components/no-workspace-onboarding";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageSwitcher } from "@/components/language-switcher";
import { useI18n } from "@/i18n/provider";
import { useAuth } from "@/hooks/use-auth";

const protectedRoutes = [
  "/dashboard",
  "/overview",
  "/leads",
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

  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-canvas text-text-primary lg:flex">
      <aside className="hidden lg:fixed lg:inset-y-0 lg:block lg:w-60">
        <AppSidebar />
      </aside>
      <div className="min-w-0 flex-1 overflow-x-hidden pb-24 lg:pb-0 lg:pl-60">
        <AppTopbar
          currentUser={currentUser}
          currentWorkspace={currentWorkspace}
          currentWorkspaceId={currentWorkspaceId}
          onOpenMenu={() => setMobileMenuOpen(true)}
          onLogout={handleLogout}
          onSwitchWorkspace={switchWorkspace}
          onWorkspaceCreated={reloadCurrentUser}
        />
        {error ? <p className="mx-4 mt-3 rounded-2xl border border-amber-400/20 bg-amber-400/10 px-4 py-3 text-sm font-semibold text-amber-100 md:mx-6">{error}</p> : null}
        {!currentWorkspaceId ? <NoWorkspaceOnboarding onWorkspaceCreated={reloadCurrentUser} onSwitchWorkspace={switchWorkspace} /> : children}
      </div>
      <nav className="mobile-bottom-nav mobile-safe-bottom fixed inset-x-0 bottom-0 z-40 border-t border-border-subtle bg-surface-1/95 px-2 py-2 shadow-[0_-12px_35px_rgba(0,0,0,0.35)] backdrop-blur-xl lg:hidden" aria-label={t("mobileNavigation.bottomNav")}>
        <div className="mx-auto grid max-w-md grid-cols-5 gap-1">
          {mobileQuickNav.map((item) => {
            const Icon = item.icon;
            const active = isActiveNav(pathname, item.href);
            return <Link key={item.href} href={item.href} className={`grid min-h-12 place-items-center rounded-2xl px-1 py-1 text-[0.68rem] font-black transition ${active ? "bg-primary text-white shadow-lg shadow-violet-500/20" : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"}`} aria-current={active ? "page" : undefined}><Icon className="h-4 w-4" aria-hidden="true" /><span className="mt-0.5 truncate">{t(item.labelKey)}</span></Link>;
          })}
        </div>
      </nav>
      {mobileMenuOpen ? (
        <div className="mobile-sidebar-drawer fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label={t("mobileNavigation.drawer")}>
          <button className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" aria-label={t("actions.close")} onClick={() => setMobileMenuOpen(false)} />
          <div className="relative h-full w-[88vw] max-w-sm overflow-hidden bg-sidebar shadow-2xl">
            <AppSidebar onNavigate={() => setMobileMenuOpen(false)} />
            <div className="mobile-sidebar-footer-compact absolute inset-x-0 bottom-0 border-t border-white/10 bg-sidebar p-3">
              <div className="mb-2 flex min-w-0 items-center gap-3 rounded-2xl bg-white/[0.06] p-3 text-sm text-slate-200">
                <div className="grid h-9 w-9 shrink-0 place-items-center rounded-2xl bg-white/10 text-xs font-black text-white">{(currentWorkspace?.workspace_name ?? "S").slice(0, 1)}</div>
                <div className="min-w-0 leading-tight" aria-label={t("mobileSidebar.profile")}>
                  <p className="truncate font-black">{currentWorkspace?.workspace_name ?? "Workspace"}</p>
                  <p className="truncate text-xs text-slate-400">{currentUser?.email}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2" aria-label={t("mobileSidebar.quickControls")}>
                <LanguageSwitcher compact />
                <ThemeToggle compact />
              </div>
              <button className="mt-2 min-h-10 w-full rounded-2xl border border-white/10 bg-white/[0.07] px-3 text-sm font-bold text-white transition hover:bg-white/10" onClick={handleLogout}>{t("actions.logout")}</button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
