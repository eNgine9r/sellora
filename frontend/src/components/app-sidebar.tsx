"use client";

import { BarChart3, Boxes, CalendarDays, Megaphone, NotebookText, PackageOpen, Settings, ShoppingBag, Sparkles, Truck, Users, WalletCards } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrandLockup } from "@/components/brand";
import { useI18n } from "@/i18n/provider";

const items = [
  ["/dashboard", "navigation.dashboard", BarChart3],
  ["/leads", "navigation.leads", Sparkles],
  ["/customers", "navigation.customers", Users],
  ["/orders", "navigation.orders", ShoppingBag],
  ["/products", "navigation.products", PackageOpen],
  ["/inventory", "navigation.inventory", Boxes],
  ["/shipments", "navigation.shipments", Truck],
  ["/advertising", "navigation.advertising", Megaphone],
  ["/finance", "navigation.finance", WalletCards],
  ["/reports", "navigation.reports", BarChart3],
  ["/calendar", "navigation.calendar", CalendarDays],
  ["/notes", "navigation.notes", NotebookText],
  ["/insights", "navigation.insights", Sparkles],
  ["/settings", "navigation.settings", Settings],
] as const;

export function AppSidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { t } = useI18n();

  return (
    <aside className="sellora-sidebar flex h-full min-h-0 flex-col border-r border-border-subtle bg-sidebar text-text-primary">
      <div className="px-4 py-5 sm:px-5">
        <Link href="/dashboard" onClick={onNavigate} aria-label={t("navigation.dashboard")} className="block rounded-[var(--radius-shell)] border border-border-subtle bg-surface-1 px-3 py-3 shadow-[var(--shadow-card)] transition hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring">
          <BrandLockup markClassName="h-10 w-10" textClassName="text-white" />
        </Link>
      </div>
      <nav className="sidebar-scrollbar grid min-w-0 gap-1 overflow-y-auto px-3 pb-44 lg:pb-5" aria-label={t("navigation.settings")}>
        {items.map(([href, label, Icon]) => {
          const active = pathname === href || pathname.startsWith(`${href}/`) || (href === "/dashboard" && pathname === "/overview") || (href === "/reports" && pathname === "/analytics");
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={`group flex min-h-11 min-w-0 items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-bold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring ${
                active ? "border border-violet-400/20 bg-primary/15 text-violet-200 shadow-[inset_0_0_0_1px_rgba(167,139,250,0.08)]" : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"
              }`}
            >
              <Icon className={`h-4 w-4 shrink-0 ${active ? "text-violet-300" : "text-text-muted group-hover:text-text-primary"}`} />
              <span className="truncate">{t(label)}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
