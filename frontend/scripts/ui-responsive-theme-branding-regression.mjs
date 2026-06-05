import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";

const files = {
  layout: "frontend/src/app/layout.tsx",
  themeProvider: "frontend/src/providers/theme-provider.tsx",
  themeToggle: "frontend/src/components/theme-toggle.tsx",
  appShell: "frontend/src/components/app-shell.tsx",
  appTopbar: "frontend/src/components/app-topbar.tsx",
  appSidebar: "frontend/src/components/app-sidebar.tsx",
  landing: "frontend/src/components/landing.tsx",
  brand: "frontend/src/components/brand.tsx",
  manifest: "frontend/public/manifest.webmanifest",
  products: "frontend/src/app/products/page.tsx",
  formDialog: "frontend/src/components/form-dialog.tsx",
  globals: "frontend/src/app/globals.css",
};

const source = Object.fromEntries(Object.entries(files).map(([key, path]) => [key, readFileSync(path, "utf8")]));

assert.equal(existsSync("frontend/public/brand/sellora-icon.svg"), true, "Sellora icon asset must exist");
assert.equal(existsSync("frontend/public/brand/sellora-logo.svg"), true, "Sellora logo asset must exist");
assert.match(source.themeProvider, /ThemeMode = "system" \| "light" \| "dark"/, "ThemeProvider must support system/light/dark modes");
assert.match(source.themeProvider, /prefers-color-scheme: dark/, "ThemeProvider must follow OS theme in system mode");
assert.match(source.themeProvider, /localStorage\.setItem\(STORAGE_KEY/, "Theme override must persist in localStorage");
assert.match(source.layout, /width: "device-width"/, "Viewport must use device width");
assert.match(source.layout, /initialScale: 1/, "Viewport must start at normal scale");
assert.match(source.layout, /ThemeProvider/, "Root layout must install ThemeProvider");
assert.match(source.themeToggle, /System theme|Light theme|Dark theme/, "Theme toggle must expose current theme labels");
assert.match(source.appShell, /bg-slate-950\/75 backdrop-blur-sm/, "Mobile drawer backdrop must be solid/readable");
assert.match(source.appShell, /overflow-hidden/, "Mobile drawer must prevent background scroll");
assert.match(source.appTopbar, /BrandIcon/, "Mobile topbar must show compact Sellora branding");
assert.match(source.appTopbar, /ThemeToggle compact/, "Theme toggle must be available in topbar/mobile");
assert.match(source.appSidebar, /text-slate-100\/90/, "Sidebar inactive nav text must remain readable");
assert.equal(source.appSidebar.includes("brightness-0 invert"), false, "Sidebar must not invert logo into placeholder square");
assert.match(source.landing, /justify-between/, "Landing header should align logo left and login right");
assert.match(source.brand, /sellora-icon\.svg/, "Brand components must use the Sellora icon asset");
assert.match(source.brand, /sellora-logo\.svg/, "Brand components must use the Sellora logo asset");
assert.match(source.manifest, /sellora-icon\.svg/, "Manifest must reference Sellora icon");
assert.match(source.manifest, /maskable/, "Manifest icon should be maskable-friendly");
assert.match(source.products, /FormDialog title="Create product"/, "Create Product must open in shared modal dialog");
assert.match(source.products, /FormDialog title="Create variant"/, "Create Variant must open in shared modal dialog");
assert.match(source.formDialog, /max-h-\[calc\(100dvh-1\.5rem\)\]/, "Shared form dialog must be mobile viewport safe");
assert.match(source.globals, /overflow-x: hidden/, "Global styles must defend against root horizontal overflow");
assert.equal(source.layout.includes(".png"), false, "Current PR-compatible PWA metadata must avoid binary PNG references");
assert.equal(source.manifest.includes(".png"), false, "Current PR-compatible manifest must avoid binary PNG references");

console.log("UI responsive theme branding regression passed");
