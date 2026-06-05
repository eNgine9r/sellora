"use client";

import { ReactNode, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { AppSidebar } from "@/components/app-sidebar";
import { AppTopbar } from "@/components/app-topbar";
import { ThemeToggle } from "@/components/theme-toggle";
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
  const { status, currentUser, currentWorkspace, currentWorkspaceId, error, logout, switchWorkspace } = useAuth();
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
  if (status === "loading") return <div className="grid min-h-screen place-items-center bg-[#F8F7FC] text-slate-600 dark:bg-[#101120] dark:text-slate-300">Loading Sellora…</div>;
  if (status === "unauthenticated") return <div className="grid min-h-screen place-items-center bg-[#F8F7FC] text-slate-600 dark:bg-[#101120] dark:text-slate-300">Redirecting to login…</div>;

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
        />
        {error ? <p className="mx-4 mt-3 rounded-2xl bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-700 md:mx-6">{error}</p> : null}
        {children}
      </div>
      {mobileMenuOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button className="absolute inset-0 bg-slate-950/75 backdrop-blur-sm" aria-label="Close menu" onClick={() => setMobileMenuOpen(false)} />
          <div className="relative h-full w-[88vw] max-w-sm overflow-hidden bg-[#080812] shadow-2xl">
            <AppSidebar onNavigate={() => setMobileMenuOpen(false)} />
            <div className="absolute inset-x-0 bottom-0 border-t border-white/10 bg-[#080812] p-4">
              <div className="mb-3 grid gap-2 rounded-2xl bg-white/[0.06] p-3 text-sm text-slate-200">
                <span className="truncate font-black">{currentWorkspace?.workspace_name ?? "Workspace"}</span>
                <span className="truncate text-xs text-slate-400">{currentUser?.email}</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <ThemeToggle />
                <button className="min-h-11 rounded-2xl border border-white/10 bg-white/10 px-3 text-sm font-bold text-white" onClick={handleLogout}>Log out</button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
