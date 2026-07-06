import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.cwd());
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
const exists = (file) => fs.existsSync(path.join(root, file));

const reportPath = "docs/sprint-7d-mobile-ux-pwa-mvp.md";
const report = exists(reportPath) ? read(reportPath) : "";
const manifestPath = "frontend/public/manifest.webmanifest";
const manifest = exists(manifestPath) ? JSON.parse(read(manifestPath)) : null;
const appShell = read("frontend/src/components/app-shell.tsx");
const topbar = read("frontend/src/components/app-topbar.tsx");
const formDialog = read("frontend/src/components/form-dialog.tsx");
const leadTable = read("frontend/src/features/leads/components/lead-table.tsx");
const orderTable = read("frontend/src/features/orders/components/order-table.tsx");
const customerTable = read("frontend/src/features/customers/components/customer-table.tsx");
const migrationFiles = fs.readdirSync(path.join(root, "backend/alembic/versions"));
const publicFiles = fs.readdirSync(path.join(root, "frontend/public"), { recursive: true }).join("\n");

const combinedFrontend = [appShell, topbar, formDialog, leadTable, orderTable, customerTable].join("\n");

const checks = [
  ["Sprint 7D QA report exists", exists(reportPath)],
  ["mobile breakpoint notes exist", report.includes("375px") && report.includes("390px") && report.includes("430px") && report.includes("768px") && report.includes("1366px")],
  ["PWA manifest exists", exists(manifestPath)],
  ["app name/short name exist", manifest?.name?.includes("Sellora") && manifest?.short_name === "Sellora"],
  ["PWA start/display/theme configured", manifest?.start_url === "/dashboard" && manifest?.display === "standalone" && Boolean(manifest?.theme_color)],
  ["mobile app shell markers exist", appShell.includes("mobile-bottom-nav") && appShell.includes("mobileQuickNav")],
  ["mobile drawer/bottom sheet markers exist", appShell.includes("mobile-sidebar-drawer") && topbar.includes("mobile-more-sheet")],
  ["responsive card/table markers exist", leadTable.includes("mobile-lead-card") && orderTable.includes("mobile-order-card") && customerTable.includes("mobile-customer-card")],
  ["mobile form sheet marker exists", formDialog.includes("mobile-form-sheet")],
  ["PWA cache/privacy policy is documented", report.includes("Service worker/offline support is intentionally deferred") && report.includes("does not cache API responses")],
  ["no API caching of private data is introduced", !/serviceWorker|caches\.open|fetch\(event\.request\)|workbox|next-pwa/i.test(combinedFrontend + "\n" + publicFiles)],
  ["no new Sprint 7D migration file was added", migrationFiles.every((file) => !/7d|mobile|pwa/i.test(file)) && report.includes("No database migration was added")],
  ["no Meta feature work was added", report.includes("No backend") || !/Meta OAuth changes added|scheduled sync added|apply-sync added/i.test(report)],
];

let failed = false;
for (const [label, ok] of checks) {
  if (ok) console.log(`OK ${label}`);
  else {
    failed = true;
    console.error(`FAIL ${label}`);
  }
}

if (failed) process.exit(1);
console.log("Mobile UX / PWA MVP regression checks passed.");
