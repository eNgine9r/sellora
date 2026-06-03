"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect } from "react";
import { useAuth } from "@/hooks/use-auth";

const protectedRoutes = ["/overview", "/leads", "/customers", "/products", "/inventory", "/orders", "/analytics", "/advertising", "/settings/import"];
const navItems = [
  { href: "/overview", label: "Overview" },
  { href: "/leads", label: "Leads" },
  { href: "/customers", label: "Customers" },
  { href: "/products", label: "Products" },
  { href: "/inventory", label: "Inventory" },
  { href: "/orders", label: "Orders" },
  { href: "/analytics", label: "Analytics" },
  { href: "/advertising", label: "Advertising" },
  { href: "/settings/import", label: "Settings → Import" },
];

function isProtectedPath(pathname: string) {
  return protectedRoutes.some((route) => pathname === route || pathname.startsWith(`${route}/`));
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { status, currentUser, currentWorkspace, currentWorkspaceId, error, logout, switchWorkspace } = useAuth();
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
    <div className="min-h-screen bg-slate-100 text-slate-950 lg:flex">
      <aside className="border-b border-slate-200 bg-slate-950 text-white lg:fixed lg:inset-y-0 lg:w-72 lg:border-b-0 lg:border-r">
        <div className="p-5">
          <Link href="/overview" className="text-2xl font-bold">Sellora</Link>
          <p className="mt-1 text-sm text-slate-300">Staging CRM workspace</p>
        </div>
        <nav className="flex gap-2 overflow-x-auto px-3 pb-4 lg:grid lg:overflow-visible">
          {navItems.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return <Link key={item.href} href={item.href} className={`whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium ${active ? "bg-blue-600 text-white" : "text-slate-200 hover:bg-slate-800"}`}>{item.label}</Link>;
          })}
        </nav>
      </aside>
      <div className="min-w-0 flex-1 lg:pl-72">
        <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur md:px-6">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-700">{currentWorkspace?.workspace_name ?? "No workspace selected"}</p>
              <p className="text-xs text-slate-500">{currentUser?.email}</p>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              {currentUser && currentUser.memberships.length > 1 ? (
                <select className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm" value={currentWorkspaceId ?? ""} onChange={(event) => switchWorkspace(event.target.value)}>
                  {currentUser.memberships.map((membership) => <option key={membership.workspace_id} value={membership.workspace_id}>{membership.workspace_name} · {membership.role}</option>)}
                </select>
              ) : null}
              <button className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50" onClick={() => { logout(); router.replace("/login"); }}>Log out</button>
            </div>
          </div>
          {error ? <p className="mt-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-700">{error}</p> : null}
        </header>
        {children}
      </div>
    </div>
  );
}
