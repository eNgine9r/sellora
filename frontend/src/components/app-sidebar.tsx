"use client";

import { BarChart3, Boxes, CalendarDays, Megaphone, NotebookText, PackageOpen, Settings, ShoppingBag, Sparkles, Truck, Users, WalletCards } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrandLogo } from "@/components/brand";

const items = [
  ["/dashboard", "Dashboard", BarChart3], ["/leads", "Leads", Sparkles], ["/customers", "Customers", Users], ["/orders", "Orders", ShoppingBag], ["/products", "Products", PackageOpen], ["/inventory", "Inventory", Boxes], ["/shipments", "Shipments", Truck], ["/advertising", "Advertising", Megaphone], ["/finance", "Finance", WalletCards], ["/reports", "Reports", BarChart3], ["/calendar", "Calendar", CalendarDays], ["/notes", "Notes", NotebookText], ["/insights", "Insights", Sparkles], ["/settings", "Settings", Settings],
] as const;

export function AppSidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return <aside className="flex h-full flex-col bg-[#080812] text-white"><div className="px-5 py-5"><Link href="/dashboard" onClick={onNavigate}><BrandLogo className="h-auto w-44 brightness-0 invert" /></Link></div><nav className="grid gap-1 overflow-y-auto px-3 pb-5">{items.map(([href, label, Icon]) => { const active = pathname === href || pathname.startsWith(`${href}/`) || (href === "/dashboard" && pathname === "/overview"); return <Link key={href} href={href} onClick={onNavigate} className={`group flex min-h-11 items-center gap-3 rounded-2xl px-4 py-3 text-sm font-bold transition ${active ? "bg-white text-violet-700 shadow-lg" : "text-slate-300 hover:bg-white/10 hover:text-white"}`}><Icon className="h-4 w-4" />{label}</Link>; })}</nav></aside>;
}
