"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { BrandIcon, BrandLogo } from "@/components/brand";
import { useAuth } from "@/hooks/use-auth";

const protectedRoutes = ["/overview", "/leads", "/customers", "/products", "/inventory", "/orders", "/shipments", "/analytics", "/advertising", "/settings/import"];
const navItems = [
  { href: "/overview", label: "Overview" },
  { href: "/leads", label: "Leads" },
  { href: "/customers", label: "Customers" },
  { href: "/products", label: "Products" },
  { href: "/inventory", label: "Inventory" },
  { href: "/orders", label: "Orders" },
  { href: "/shipments", label: "Shipments" },
  { href: "/analytics", label: "Analytics" },
  { href: "/advertising", label: "Advertising" },
  { href: "/settings/import", label: "Settings → Import" },
];

function isProtectedPath(pathname: string) {
  return protectedRoutes.some((route) => pathname === route || pathname.startsWith(`${route}/`));
}

function NavigationLinks({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <nav className="grid gap-2">
      {navItems.map((item) => {
        const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
        return <Link key={item.href} href={item.href} onClick={onNavigate} className={`rounded-xl px-4 py-3 text-sm font-semibold transition ${active ? "bg-blue-600 text-white" : "text-slate-200 hover:bg-slate-800"}`}>{item.label}</Link>;
      })}
    </nav>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { status, currentUser, currentWorkspace, currentWorkspaceId, error, logout, switchWorkspace } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const protectedPath = isProtectedPath(pathname);

  useEffect(() => {
    if (protectedPath && status === "unauthenticated") {
      router.replace("/login");
    }
  }, [protectedPath, router, status]);

  if (!protectedPath) {
    return <>{children}</>;
  }

  if (status === "loading") {
    return <div className="grid min-h-screen place-items-center bg-slate-100 text-slate-600">Loading Sellora…</div>;
  }

  if (status === "unauthenticated") {
    return <div className="grid min-h-screen place-items-center bg-slate-100 text-slate-600">Redirecting to login…</div>;
  }

  return (
    <div className="min-h-screen overflow-x-hidden bg-slate-100 text-slate-950 lg:flex">
      <aside className="hidden bg-slate-950 text-white lg:fixed lg:inset-y-0 lg:block lg:w-72 lg:border-r lg:border-slate-800">
        <div className="p-5">
          <Link href="/overview" className="block" aria-label="Sellora overview"><BrandLogo className="h-auto w-44" /></Link>
          <p className="mt-3 text-sm text-slate-300">Staging CRM workspace</p>
        </div>
        <div className="px-3 pb-4"><NavigationLinks pathname={pathname} /></div>
      </aside>

      <div className="min-w-0 flex-1 lg:pl-72">
        <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur md:px-6">
          <div className="mb-3 flex items-center justify-between lg:hidden">
            <Link href="/overview" className="flex items-center gap-3" aria-label="Sellora overview"><BrandIcon className="h-10 w-10 rounded-xl" /><span className="text-lg font-extrabold">Sellora</span></Link>
            <button className="rounded-xl border border-slate-300 px-4 py-3 text-sm font-bold text-slate-700" onClick={() => setMobileMenuOpen(true)}>Menu</button>
          </div>
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-700">{currentWorkspace?.workspace_name ?? "No workspace selected"}</p>
              <p className="break-all text-xs text-slate-500">{currentUser?.email}</p>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              {currentUser && currentUser.memberships.length > 1 ? (
                <select className="min-h-11 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm" value={currentWorkspaceId ?? ""} onChange={(event) => switchWorkspace(event.target.value)}>
                  {currentUser.memberships.map((membership) => <option key={membership.workspace_id} value={membership.workspace_id}>{membership.workspace_name} · {membership.role}</option>)}
                </select>
              ) : null}
              <button className="min-h-11 rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50" onClick={() => { logout(); router.replace("/login"); }}>Log out</button>
            </div>
          </div>
          {error ? <p className="mt-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-700">{error}</p> : null}
        </header>
        {children}
      </div>

      {mobileMenuOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button className="absolute inset-0 bg-slate-950/60" aria-label="Close menu" onClick={() => setMobileMenuOpen(false)} />
          <aside className="relative h-full w-[85vw] max-w-sm overflow-y-auto bg-slate-950 p-5 text-white shadow-2xl">
            <div className="mb-6 flex items-center justify-between">
              <BrandLogo className="h-auto w-40" />
              <button className="rounded-xl border border-slate-700 px-4 py-3 text-sm font-bold" onClick={() => setMobileMenuOpen(false)}>Close</button>
            </div>
            <NavigationLinks pathname={pathname} onNavigate={() => setMobileMenuOpen(false)} />
          </aside>
        </div>
      ) : null}
    </div>
  );
}
