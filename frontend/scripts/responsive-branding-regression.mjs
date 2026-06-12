import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";

const layout = readFileSync("frontend/src/app/layout.tsx", "utf8");
const sidebar = readFileSync("frontend/src/components/app-sidebar.tsx", "utf8");
const landing = readFileSync("frontend/src/components/landing.tsx", "utf8");
const login = readFileSync("frontend/src/app/login/page.tsx", "utf8");
const manifest = readFileSync("frontend/public/manifest.webmanifest", "utf8");

for (const file of [
  "frontend/public/brand/sellora-icon.svg",
  "frontend/public/brand/sellora-logo.svg",
]) assert.equal(existsSync(file), true, `${file} must exist`);

assert.match(layout, /manifest: "\/manifest\.webmanifest"/, "Next metadata must reference the web app manifest");
assert.match(layout, /apple: \[\{ url: "\/brand\/sellora-icon\.svg"/, "Next metadata must reference the SVG Sellora icon for Apple touch metadata");
assert.match(manifest, /sellora-icon\.svg/, "Manifest must include the SVG Sellora icon");
assert.match(manifest, /maskable/, "Manifest icon should include maskable purpose");
assert.match(sidebar, /BrandLockup/, "Authenticated sidebar must use the Sellora brand lockup");
assert.equal(sidebar.includes("brightness-0 invert"), false, "Sidebar must not invert the logo into a white square");
assert.match(landing, /Операційна система для продажів з Instagram/, "Landing page should use polished hero copy");
assert.match(login, /BrandLockup/, "Login page must use Sellora brand lockup");
assert.match(login, /noValidate/, "Login form should use app-styled validation instead of native popups");

assert.equal(layout.includes(".png"), false, "PWA metadata must avoid binary PNG assets for PR compatibility");
assert.equal(manifest.includes(".png"), false, "Manifest must avoid binary PNG assets for PR compatibility");

console.log("Responsive branding regression passed");
