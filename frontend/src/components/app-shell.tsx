"use client";

import { ReactNode, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { AppSidebar } from "@/components/app-sidebar";
import { AppTopbar } from "@/components/app-topbar";
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

  if (!protectedPath) return <>{children}</>;
  if (status === "loading") return <div className="grid min-h-screen place-items-center bg-[#F8F7FC] text-slate-600">Loading Sellora…</div>;
  if (status === "unauthenticated") return <div className="grid min-h-screen place-items-center bg-[#F8F7FC] text-slate-600">Redirecting to login…</div>;

  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-[#F8F7FC] text-[#111827] lg:flex">
      <aside className="hidden lg:fixed lg:inset-y-0 lg:block lg:w-72">
        <AppSidebar />
      </aside>
      <div className="min-w-0 flex-1 overflow-x-hidden lg:pl-72">
        <AppTopbar
          currentUser={currentUser}
          currentWorkspace={currentWorkspace}
          currentWorkspaceId={currentWorkspaceId}
          onOpenMenu={() => setMobileMenuOpen(true)}
          onLogout={() => {
            logout();
            router.replace("/login");
          }}
          onSwitchWorkspace={switchWorkspace}
        />
        {error ? <p className="mx-4 mt-3 rounded-2xl bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-700 md:mx-6">{error}</p> : null}
        {children}
      </div>
      {mobileMenuOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button className="absolute inset-0 bg-slate-950/60" aria-label="Close menu" onClick={() => setMobileMenuOpen(false)} />
          <div className="relative h-full w-[88vw] max-w-sm overflow-hidden shadow-2xl">
            <AppSidebar onNavigate={() => setMobileMenuOpen(false)} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
