import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (path) => readFileSync(path, "utf8");
const shell = read("frontend/src/components/app-shell.tsx");
const brand = read("frontend/src/components/brand.tsx");
const sidebar = read("frontend/src/components/app-sidebar.tsx");
const topbar = read("frontend/src/components/app-topbar.tsx");
const checks = [
  ["desktop-only brand cell", shell.includes('data-shell-brand-cell') && shell.includes('className="relative hidden') && shell.includes("lg:flex lg:h-[var(--topbar-height)]")],
  ["desktop brand is separate from mobile BrandLockup", shell.includes("import { DesktopBrandLockup }") && shell.includes("<DesktopBrandLockup />") && brand.includes("export function BrandLockup(")],
  ["brand is unboxed, not a card/button", shell.includes('className="group relative flex w-full min-w-0 items-center rounded-xl py-1 transition-opacity') && !shell.includes('rounded-2xl border border-transparent px-1 py-1')],
  ["desktop logo and wordmark on one aligned line", brand.includes('data-desktop-brand-lockup') && brand.includes('flex min-w-0 items-center gap-3')],
  ["compact logo asset is unchanged", brand.includes('/brand/sellora-icon.webp') && brand.includes('h-9 w-9')],
  ["legible wordmark and secondary descriptor", brand.includes('text-[20px]') && brand.includes('CRM Platform')],
  ["logo cell and desktop navigation share surface", shell.includes("border-b border-r border-border-subtle bg-sidebar") && sidebar.includes('bg-sidebar')],
  ["brand and sidebar widths share a CSS variable", shell.includes("lg:[--sidebar-width:232px]") && shell.includes("2xl:[--sidebar-width:244px]") && shell.includes("lg:w-[var(--sidebar-width)]")],
  ["desktop shell layout keeps its topbar track", shell.includes("lg:[--topbar-height:72px]") && shell.includes("lg:[grid-template-columns:var(--sidebar-width)_minmax(0,1fr)]")],
  ["desktop branding preserves dashboard route", shell.includes('<Link href="/dashboard" aria-label={t("navigation.dashboard")}')],
  ["mobile drawer uses unchanged branding and footer", sidebar.includes("mobile-sidebar-brand") && sidebar.includes('<BrandLockup markClassName="h-8 w-8"') && shell.includes("mobile-sidebar-footer-compact")],
  ["mobile topbar remains independent", topbar.includes('mobile-brand-lockup') && shell.includes("<AppTopbar")],
  ["existing mobile scroll lock remains", shell.includes('body.style.position = "fixed"') && shell.includes('mobile-sidebar-drawer fixed inset-0')],
];
for (const [name, ok] of checks) {
  if (!ok) console.error("FAIL:", name);
}
assert.ok(checks.every(([, ok]) => ok), "Desktop sidebar logo/layout regression");
console.log(`Desktop sidebar branding regression PASS (${checks.length} checks)`);
