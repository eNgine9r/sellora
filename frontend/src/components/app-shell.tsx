"use client";

import { ReactNode, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { AppSidebar } from "@/components/app-sidebar";
import { AppTopbar } from "@/components/app-topbar";
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
  if (status === "loading") return <div className="grid min-h-screen place-items-center bg-[#F8F7FC] text-slate-600 dark:bg-[#101120] dark:text-slate-300">{t("common.loadingSellora")}</div>;
  if (status === "unauthenticated") return <div className="grid min-h-screen place-items-center bg-[#F8F7FC] text-slate-600 dark:bg-[#101120] dark:text-slate-300">{t("common.redirectingLogin")}</div>;

  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-[#F8F7FC] text-[#111827] dark:bg-[#101120] dark:text-slate-100 lg:flex">
      <aside className="hidden lg:fixed lg:inset-y-0 lg:block lg:w-72">
        <AppSidebar />
      </aside>
      <div className="min-w-0 flex-1 overflow-x-hidden lg:pl-72">
        <AppTopbar
          currentUser={currentUser}
          currentWorkspace={currentWorkspace}
          currentWorkspaceId={currentWorkspaceId}
          onOpenMenu={() => setMobileMenuOpen(true)}
          onLogout={handleLogout}
          onSwitchWorkspace={switchWorkspace}
          onWorkspaceCreated={reloadCurrentUser}
        />
        {error ? <p className="mx-4 mt-3 rounded-2xl bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-700 md:mx-6">{error}</p> : null}
        {children}
      </div>
      {mobileMenuOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button className="absolute inset-0 bg-slate-950/75 backdrop-blur-sm" aria-label="Close menu" onClick={() => setMobileMenuOpen(false)} />
          <div className="relative h-full w-[88vw] max-w-sm overflow-hidden bg-[#080812] shadow-2xl">
            <AppSidebar onNavigate={() => setMobileMenuOpen(false)} />
            <div className="mobile-sidebar-footer-compact absolute inset-x-0 bottom-0 border-t border-white/10 bg-[#080812] p-3">
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
