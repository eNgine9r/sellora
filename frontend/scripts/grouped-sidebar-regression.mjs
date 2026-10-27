import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const sidebar = readFileSync("frontend/src/components/app-sidebar.tsx", "utf8");
const shell = readFileSync("frontend/src/components/app-shell.tsx", "utf8");
const uk = JSON.parse(readFileSync("frontend/src/i18n/messages/uk.json", "utf8"));
const en = JSON.parse(readFileSync("frontend/src/i18n/messages/en.json", "utf8"));

const groups = ["main", "operations", "growth", "organization", "system"];
const paths = [
  "/dashboard", "/leads", "/direct", "/customers", "/orders",
  "/products", "/inventory", "/shipments",
  "/advertising", "/finance", "/reports", "/insights",
  "/calendar", "/notes", "/settings",
];
for (const group of groups) {
  assert.match(sidebar, new RegExp('id: "' + group + '"'), `Sidebar group ${group} is missing`);
  assert.ok(uk.navigationGroups[group] && en.navigationGroups[group], `Section ${group} requires UK/EN titles`);
}
for (const path of paths) {
  const occurrences = [...sidebar.matchAll(/\["(\/[\w-]+)",\s*"navigation\./g)].filter(m => m[1] === path);
  assert.equal(occurrences.length, 1, `Canonical sidebar link ${path} should appear exactly once`);
}
const order = groups.map(g => sidebar.indexOf('id: "' + g + '"'));
assert.ok(order.every((v, i) => i === 0 || v > order[i - 1]), "Group order must be workflow-first");
assert.ok(sidebar.includes('pathname.startsWith(`${href}/`)'), "Subroute activation must remain");
assert.ok(sidebar.includes('pathname === "/overview"'), "Dashboard alias must remain");
assert.ok(sidebar.includes('pathname === "/analytics"'), "Reports alias must remain");
assert.ok(sidebar.includes('aria-current={active ? "page" : undefined}'), "Active route must be announced");
assert.ok(sidebar.includes('aria-expanded={opened}') && sidebar.includes('aria-controls={`sidebar-group-${group.id}`}'), "Disclosure buttons must announce their state and panel");
assert.ok(sidebar.includes('className="flex min-h-11 w-full'), "Section header must be 44px and full-width tappable");
assert.ok(sidebar.includes('const opened = group.id === "main" || expanded[group.id]'), "Primary navigation should remain expanded");
assert.ok(sidebar.includes('growth: navigationGroups[2].items.some') && sidebar.includes('organization: navigationGroups[3].items.some'), "Secondary mobile groups must reveal active route by default");
assert.ok(sidebar.includes('hidden lg:grid'), "Collapsed secondary sections should remain accessible on desktop");
assert.ok(sidebar.includes('className={`min-w-0 gap-1 ${opened ? "grid" : "hidden lg:grid"}`}'), "Mobile hidden state must not be overridden by an unconditional grid display class");
assert.ok(sidebar.includes('const mobileHidden = group.id === "system"') && sidebar.includes('hidden lg:block'), "Settings belongs in one place: mobile footer / desktop System");
assert.ok(sidebar.includes('onClick={onNavigate}') && sidebar.includes('aria-label={t("actions.close")}'), "Drawer close button and link navigation should work");
assert.ok(shell.includes('mobile-sidebar-footer-compact') && shell.includes('href="/settings" onClick={() => setMobileMenuOpen(false)}'), "Mobile footer keeps only Settings shortcut");
assert.ok(shell.includes('event.key === "Escape"'), "Escape should close mobile navigation");
assert.ok(shell.includes('mobile-sidebar-drawer') && shell.includes('grid-rows-[minmax(0,1fr)_auto]'), "Drawer must preserve scrollable nav and fixed safe footer");
assert.ok(shell.includes('mobile-bottom-nav'), "Bottom navigation must remain intact");
console.log(`Grouped sidebar regression passed (${paths.length} unique routes; ${groups.length} localized sections).`);
