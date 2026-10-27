"use client";

import { useEffect, useState } from "react";
import { BarChart3, Boxes, CalendarDays, ChevronDown, Megaphone, MessageCircle, NotebookText, PackageOpen, Settings, ShoppingBag, Sparkles, Truck, Users, WalletCards } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrandLockup } from "@/components/brand";
import { useI18n } from "@/i18n/provider";

// A single source of truth for the mobile drawer and the desktop sidebar.
// Keep API routes and the existing dashboard/reports aliases unchanged.
const navigationGroups = [
  {
    id: "main",
    label: "navigationGroups.main",
    items: [
      ["/dashboard", "navigation.dashboard", BarChart3],
      ["/leads", "navigation.leads", Sparkles],
      ["/direct", "navigation.direct", MessageCircle],
      ["/customers", "navigation.customers", Users],
      ["/orders", "navigation.orders", ShoppingBag],
    ],
  },
  {
    id: "operations",
    label: "navigationGroups.operations",
    items: [
      ["/products", "navigation.products", PackageOpen],
      ["/inventory", "navigation.inventory", Boxes],
      ["/shipments", "navigation.shipments", Truck],
    ],
  },
  {
    id: "growth",
    label: "navigationGroups.growth",
    items: [
      ["/advertising", "navigation.advertising", Megaphone],
      ["/finance", "navigation.finance", WalletCards],
      ["/reports", "navigation.reports", BarChart3],
      ["/insights", "navigation.insights", Sparkles],
    ],
  },
  {
    id: "organization",
    label: "navigationGroups.organization",
    items: [
      ["/calendar", "navigation.calendar", CalendarDays],
      ["/notes", "navigation.notes", NotebookText],
    ],
  },
  {
    id: "system",
    label: "navigationGroups.system",
    items: [
      ["/settings", "navigation.settings", Settings],
    ],
  },
] as const;

type GroupId = (typeof navigationGroups)[number]["id"];

function isActiveNav(pathname: string, href: string) {
  return pathname === href
    || pathname.startsWith(`${href}/`)
    || (href === "/dashboard" && pathname === "/overview")
    || (href === "/reports" && (pathname === "/analytics" || pathname.startsWith("/analytics/")));
}

export function AppSidebar({ onNavigate, showBrand = true }: { onNavigate?: () => void; showBrand?: boolean }) {
  const pathname = usePathname();
  const { t } = useI18n();

  // On phones, the two lower-priority groups start collapsed. Automatically
  // reveal the active group on direct navigation and after route changes.
  const [expanded, setExpanded] = useState<Record<GroupId, boolean>>(() => ({
    main: true,
    operations: true,
    growth: navigationGroups[2].items.some(([href]) => isActiveNav(pathname, href)),
    organization: navigationGroups[3].items.some(([href]) => isActiveNav(pathname, href)),
    system: true,
  }));

  useEffect(() => {
    const activeGroup = navigationGroups.find((group) =>
      group.items.some(([href]) => isActiveNav(pathname, href)),
    );
    if (activeGroup) setExpanded((previous) => previous[activeGroup.id] ? previous : { ...previous, [activeGroup.id]: true });
  }, [pathname]);

  return (
    <aside className="sellora-sidebar flex h-full min-h-0 min-w-0 flex-col overflow-hidden border-r border-border-subtle bg-sidebar text-text-primary" data-sidebar-groups>
      {showBrand ? (
        <div className="mobile-sidebar-brand shrink-0 px-3 pb-1 pt-3 sm:px-4">
          <Link
            href="/dashboard"
            onClick={onNavigate}
            aria-label={t("navigation.dashboard")}
            className="flex min-h-[60px] min-w-0 items-center rounded-2xl border border-border-subtle bg-surface-1/75 px-3 py-2 transition hover:border-primary/20 hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
          >
            <BrandLockup markClassName="h-8 w-8" textClassName="text-text-primary" />
          </Link>
        </div>
      ) : null}

      <nav className="sidebar-scrollbar flex min-h-0 min-w-0 flex-1 flex-col gap-3 overflow-y-auto overscroll-contain px-3 pb-4 pt-3 lg:gap-4 lg:pt-5" aria-label={t("mobileNavigation.drawer")}>
        {navigationGroups.map((group) => {
          const mobileHidden = group.id === "system";
          const opened = group.id === "main" || expanded[group.id];

          return (
            <section key={group.id} className={`min-w-0 ${mobileHidden ? "hidden lg:block" : ""}`} data-sidebar-section={group.id}>
              {group.id !== "main" ? <div className="mx-2 mb-2 border-t border-border-subtle/70" aria-hidden="true" /> : null}
              <div className="mb-1 flex min-h-8 items-center justify-between px-2">
                <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-text-muted">{t(group.label)}</span>
                {group.id !== "main" && group.id !== "system" ? (
                  <button
                    type="button"
                    className="inline-flex h-9 min-w-9 items-center justify-center rounded-lg text-text-muted transition hover:bg-surface-hover hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring lg:hidden"
                    aria-label={`${t(group.label)}: ${opened ? t("navigationGroups.collapse") : t("navigationGroups.expand")}`}
                    aria-expanded={opened}
                    aria-controls={`sidebar-group-${group.id}`}
                    onClick={() => setExpanded((previous) => ({ ...previous, [group.id]: !previous[group.id] }))}
                  >
                    <ChevronDown className={`h-4 w-4 transition-transform duration-200 ${opened ? "rotate-180" : ""}`} aria-hidden="true" />
                  </button>
                ) : null}
              </div>
              <div id={`sidebar-group-${group.id}`} className={`grid min-w-0 gap-1 ${opened ? "" : "hidden lg:grid"}`}>
                {group.items.map(([href, label, Icon]) => {
                  const active = isActiveNav(pathname, href);
                  return (
                    <Link
                      key={href}
                      href={href}
                      onClick={onNavigate}
                      aria-current={active ? "page" : undefined}
                      className={`group relative flex min-h-12 min-w-0 items-center gap-3 rounded-xl border px-3 py-2.5 text-[13px] font-semibold transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring lg:min-h-10 lg:py-2 ${
                        active
                          ? "border-primary/25 bg-primary/10 text-primary shadow-[inset_0_0_0_1px_rgba(167,139,250,0.05)]"
                          : "border-transparent text-text-secondary hover:border-border-subtle hover:bg-surface-hover hover:text-text-primary"
                      }`}
                    >
                      {active ? <span className="absolute bottom-2 left-0 top-2 w-[3px] rounded-r-full bg-primary" aria-hidden="true" /> : null}
                      <Icon className={`h-[18px] w-[18px] shrink-0 transition-colors lg:h-4 lg:w-4 ${active ? "text-primary" : "text-text-muted group-hover:text-text-primary"}`} aria-hidden="true" />
                      <span className="truncate">{t(label)}</span>
                    </Link>
                  );
                })}
              </div>
            </section>
          );
        })}
      </nav>
    </aside>
  );
}
