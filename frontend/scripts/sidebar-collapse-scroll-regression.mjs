import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (p) => readFileSync(p, "utf8");
const shell = read("frontend/src/components/app-shell.tsx");
const sidebar = read("frontend/src/components/app-sidebar.tsx");
const styles = read("frontend/src/app/globals.css");
const uk = JSON.parse(read("frontend/src/i18n/messages/uk.json"));
const en = JSON.parse(read("frontend/src/i18n/messages/en.json"));

const checks = [
  ["desktop mode stored per device", shell.includes('sellora:sidebar:collapsed:v1') && shell.includes("localStorage.getItem") && shell.includes("localStorage.setItem")],
  ["collapsed and expanded widths", shell.includes("--sidebar-width:76px") && shell.includes("--sidebar-width:232px") && shell.includes("--sidebar-width:244px")],
  ["single desktop grid sizes both tracks", shell.includes("grid-template-columns:var(--sidebar-width)_minmax(0,1fr)") && shell.includes("grid-template-rows:var(--topbar-height)_minmax(0,1fr)")],
  ["fixed desktop viewport", shell.includes("lg:h-dvh") && shell.includes("lg:min-h-0") && shell.includes("lg:overflow-hidden")],
  ["desktop scroll host does not grow", shell.includes('data-sidebar-scroll-host') && shell.includes("lg:overflow-hidden lg:[grid-column:1]")],
  ["main content independently scrolls", shell.includes('data-main-scroll-region') && shell.includes("lg:overflow-y-auto lg:overscroll-contain")],
  ["sidebar independently scrolls", sidebar.includes("data-sidebar-scroll-region") && sidebar.includes("min-h-0 min-w-0 flex-1") && sidebar.includes("overflow-y-auto overscroll-contain")],
  ["desktop scroller rule retains min height zero", styles.includes('[data-sidebar-scroll-host] { min-height: 0;') && styles.includes('[data-sidebar-scroll-region] { min-height: 0;')],
  ["scrollbar readable in both themes", styles.includes("scrollbar-color: var(--border-strong)") && styles.includes("background: var(--border-strong)")],
  ["toggle pinned outside scroll", sidebar.indexOf("data-sidebar-desktop-controls") < sidebar.indexOf("data-sidebar-scroll-region")],
  ["toggle works both ways", sidebar.includes("data-sidebar-collapse-toggle") && sidebar.includes("onClick={onToggleCollapsed}") && sidebar.includes("PanelLeftOpen") && sidebar.includes("PanelLeftClose")],
  ["collapsed mode retains icon-only labels", sidebar.includes('collapsed ? "lg:sr-only"') && sidebar.includes('aria-label={collapsed ? t(label) : undefined}') && sidebar.includes('title={collapsed ? t(label) : undefined}')],
  ["active navigation and aliases preserved", sidebar.includes('aria-current={active ? "page" : undefined}') && sidebar.includes('pathname === "/overview"') && sidebar.includes('pathname === "/analytics"')],
  ["desktop brand shrinks to logo", shell.includes('sidebarCollapsed ? <BrandIcon') && shell.includes('<DesktopBrandLockup />')],
  ["mobile drawer ignores collapse state", shell.includes('<AppSidebar onNavigate={() => setMobileMenuOpen(false)} />') && shell.includes("mobile-sidebar-drawer")],
  ["mobile body scroll lock unchanged", shell.includes('body.style.position = "fixed"') && shell.includes("window.scrollTo(0, scrollY)")],
  ["motion preferences honored", shell.includes("motion-reduce:transition-none")],
  ["localization complete", [uk,en].every(loc => loc.sidebarLayout.navigation && loc.sidebarLayout.collapse && loc.sidebarLayout.expand)],
];
for (const [title, ok] of checks) if (!ok) console.error("FAIL",title);
assert.ok(checks.every(([,ok])=>ok), "Sidebar collapse + desktop scrolling regression");
console.log("Sidebar collapse/scroll regression PASS (" + checks.length + " checks).");
