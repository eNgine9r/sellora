"use client";

import { BarChart3, Boxes, CalendarDays, Megaphone, NotebookText, PackageOpen, Settings, ShoppingBag, Sparkles, Truck, Users, WalletCards } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrandLockup } from "@/components/brand";

const items = [
  ["/dashboard", "Dashboard", BarChart3],
  ["/leads", "Leads", Sparkles],
  ["/customers", "Customers", Users],
  ["/orders", "Orders", ShoppingBag],
  ["/products", "Products", PackageOpen],
  ["/inventory", "Inventory", Boxes],
  ["/shipments", "Shipments", Truck],
  ["/advertising", "Advertising", Megaphone],
  ["/finance", "Finance", WalletCards],
  ["/reports", "Reports", BarChart3],
  ["/calendar", "Calendar", CalendarDays],
  ["/notes", "Notes", NotebookText],
  ["/insights", "Insights", Sparkles],
  ["/settings", "Settings", Settings],
] as const;

export function AppSidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <aside className="flex h-full min-h-0 flex-col bg-[radial-gradient(circle_at_top_left,rgba(109,40,217,.35),transparent_36%),#080812] text-white">
      <div className="px-4 py-5 sm:px-5">
        <Link href="/dashboard" onClick={onNavigate} aria-label="Sellora dashboard" className="block rounded-3xl border border-white/10 bg-white/[0.04] px-3 py-3 shadow-2xl shadow-black/20 transition hover:bg-white/[0.07]">
          <BrandLockup markClassName="h-10 w-10" textClassName="text-white" />
        </Link>
      </div>
      <nav className="grid min-w-0 gap-1 overflow-y-auto px-3 pb-44 lg:pb-5" aria-label="Main navigation">
        {items.map(([href, label, Icon]) => {
          const active = pathname === href || pathname.startsWith(`${href}/`) || (href === "/dashboard" && pathname === "/overview");
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={`group flex min-h-11 min-w-0 items-center gap-3 rounded-2xl px-4 py-3 text-sm font-bold transition ${
                active ? "bg-white text-violet-700 shadow-lg" : "text-slate-100/90 hover:bg-white/10 hover:text-white"
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="truncate">{label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
