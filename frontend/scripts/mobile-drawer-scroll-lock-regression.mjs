import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const shell = readFileSync("frontend/src/components/app-shell.tsx", "utf8");
const css = readFileSync("frontend/src/app/globals.css", "utf8");
const sidebar = readFileSync("frontend/src/components/app-sidebar.tsx", "utf8");
const checks = [
  ["lock only while drawer is open", shell.includes("if (!mobileMenuOpen) return;")],
  ["record exact page scroll position", shell.includes("const scrollY = window.scrollY")],
  ["freeze body in iOS Safari rather than relying on overflow-hidden", shell.includes('body.style.position = "fixed"') && shell.includes('body.style.top = `-${scrollY}px`')],
  ["stabilize body width during lock", ['left = "0"', 'right = "0"', 'width = "100%"'].every(part => shell.includes("body.style." + part))],
  ["prevent root scroll and iOS rubber-banding", shell.includes('html.style.overflow = "hidden"') && shell.includes('html.style.overscrollBehavior = "none"')],
  ["restore all prior body and root inline styles", ["position","top","left","right","width","overflow"].every(field => shell.includes(`body.style.${field} = previous.${field}`)) && shell.includes("html.style.overflow = previous.htmlOverflow") && shell.includes("html.style.overscrollBehavior = previous.htmlOverscroll")],
  ["restore original scroll position", shell.includes("window.scrollTo(0, scrollY)")],
  ["clear desktop breakpoint when drawer was opened on phone", shell.includes('window.matchMedia("(min-width: 1024px)")') && shell.includes('desktop.removeEventListener("change", closeOnDesktop)')],
  ["avoid concurrent bottom more sheet", shell.includes("setMobileMoreOpen(false); setMobileMenuOpen(true);")],
  ["logout releases drawer lock", shell.includes("await logout();\n      setMobileMenuOpen(false);")],
  ["backdrop blocks touch propagation", shell.includes("absolute inset-0 touch-none bg-[var(--overlay-background)]")],
  ["drawer uses dynamic mobile viewport and no scroll chaining", shell.includes('mobile-sidebar-drawer fixed inset-0 z-[80] h-[100dvh] overscroll-none')],
  ["drawer content stays independently scrollable", sidebar.includes("overflow-y-auto overscroll-contain") && css.includes("overscroll-behavior-y: contain;") && css.includes("-webkit-overflow-scrolling: touch;") && css.includes("touch-action: pan-y;")],
  ["footer remains outside the independently scrollable sidebar", shell.includes('grid-rows-[minmax(0,1fr)_auto]') && shell.includes('mobile-sidebar-footer-compact')],
  ["existing closing behavior preserved", shell.includes('onClick={() => setMobileMenuOpen(false)}') && shell.includes('event.key === "Escape"')],
];
for (const [label, passed] of checks) {
  if (!passed) console.error("FAIL:", label);
}
assert.ok(checks.every(([, passed]) => passed), "iOS drawer/background scroll lock regression");
console.log(`Mobile drawer scroll lock regression passed (${checks.length} checks)`);
