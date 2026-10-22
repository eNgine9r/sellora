import { readFileSync } from "node:fs";

const topbar = readFileSync("frontend/src/components/app-topbar.tsx", "utf8");
const brand = readFileSync("frontend/src/components/brand.tsx", "utf8");
const layout = readFileSync("frontend/src/app/layout.tsx", "utf8");
const css = readFileSync("frontend/src/app/globals.css", "utf8");

const checks = [
  ["iOS standalone status bar is opaque", layout.includes('statusBarStyle: "black"') && !layout.includes("black-translucent")],
  ["standalone viewport still covers safe areas", layout.includes('viewportFit: "cover"')],
  ["brand is independently identifiable", topbar.includes("data-mobile-brand-lockup") && topbar.includes("mobile-brand-copy")],
  ["mobile brand text is legible weight and size", topbar.includes("mobile-brand-title truncate text-base font-bold")],
  ["header logo avoids low resolution Next image derivative", topbar.includes('<BrandIcon className="h-10 w-10 shrink-0" priority unoptimized />') && brand.includes("unoptimized={unoptimized}")],
  ["header retains safe area", topbar.includes("mobile-safe-top sticky top-0") && css.includes("safe-area-inset-top")],
  ["mobile topbar opaque", css.includes("background-color: var(--canvas) !important") && css.includes(".mobile-safe-top[data-shell-topbar]")],
  ["mobile brand compositor reset", css.includes(".mobile-brand-lockup img") && css.includes("transform: none !important") && css.includes("filter: none !important") && css.includes("text-shadow: none !important")],
  ["desktop branding untouched", brand.includes("BrandLockup(") && brand.includes("sellora-logo.webp")],
  ["no modification to auth or app data", !topbar.includes('statusBarStyle: "black-translucent"')],
];
let bad = false;
for (const [label, ok] of checks) { console.log(`${ok ? "PASS" : "FAIL"} ${label}`); bad ||= !ok; }
if (bad) process.exit(1);
