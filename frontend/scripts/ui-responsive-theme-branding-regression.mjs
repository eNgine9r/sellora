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
  leads: "frontend/src/app/leads/page.tsx",
  customers: "frontend/src/app/customers/page.tsx",
  products: "frontend/src/app/products/page.tsx",
  orders: "frontend/src/app/orders/page.tsx",
  shipmentsPage: "frontend/src/app/shipments/page.tsx",
  shipmentDetails: "frontend/src/features/shipments/components/shipment-details.tsx",
  dashboardPage: "frontend/src/app/dashboard/page.tsx",
  dashboardKpi: "frontend/src/features/dashboard/components/kpi-card.tsx",
  recentOrders: "frontend/src/features/dashboard/components/recent-orders-table.tsx",
  topProducts: "frontend/src/features/dashboard/components/top-products-card.tsx",
  advertising: "frontend/src/app/advertising/page.tsx",
  formDialog: "frontend/src/components/form-dialog.tsx",
  editDialog: "frontend/src/components/edit-record-dialog.tsx",
  confirmDialog: "frontend/src/components/confirm-action-dialog.tsx",
  orderForm: "frontend/src/features/orders/components/order-form.tsx",
  inventory: "frontend/src/app/inventory/page.tsx",
  importPage: "frontend/src/app/settings/import/page.tsx",
  importUpload: "frontend/src/features/import-center/components/import-upload-card.tsx",
  sheetSelector: "frontend/src/features/import-center/components/sheet-selector.tsx",
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
assert.doesNotMatch(source.themeToggle, /Monitor|System theme[\s\S]*<Monitor/, "Topbar theme toggle must not expose confusing PC/monitor icon");
assert.match(source.themeToggle, /setMode\(nextMode\)/, "Theme toggle must switch directly between light/dark after system default");
assert.match(source.appShell, /bg-slate-950\/75 backdrop-blur-sm/, "Mobile drawer backdrop must be solid/readable");
assert.match(source.appShell, /overflow-hidden/, "Mobile drawer must prevent background scroll");
assert.match(source.appTopbar, /mobile-safe-top/, "Mobile topbar must respect safe areas");
assert.match(source.appTopbar, /BrandIcon/, "Mobile topbar must show compact Sellora branding");
assert.match(source.appTopbar, /ThemeToggle compact/, "Theme toggle must be available in topbar/mobile");
assert.match(source.appSidebar, /sellora-sidebar/, "Sidebar must use stable dark premium surface marker");
assert.match(source.appSidebar, /sidebar-scrollbar/, "Sidebar must use custom scrollbar class");
assert.match(source.appSidebar, /text-slate-100\/90/, "Sidebar inactive nav text must remain readable");
assert.equal(source.appSidebar.includes("brightness-0 invert"), false, "Sidebar must not invert logo into placeholder square");
assert.match(source.landing, /justify-between/, "Landing header should align logo left and login right");
assert.match(source.brand, /sellora-icon\.svg/, "Brand components must use the Sellora icon asset");
assert.match(source.brand, /sellora-logo\.svg/, "Brand components must use the Sellora logo asset");
assert.match(source.manifest, /sellora-icon\.svg/, "Manifest must reference Sellora icon");
assert.match(source.manifest, /maskable/, "Manifest icon should be maskable-friendly");
assert.match(source.leads, /FormDialog title="Create lead"/, "Create Lead must open in shared modal dialog");
assert.match(source.customers, /FormDialog title="Create customer"/, "Create Customer must open in shared modal dialog");
assert.match(source.products, /FormDialog title="Create product"/, "Create Product must open in shared modal dialog");
assert.match(source.products, /FormDialog title="Create variant"/, "Create Variant must open in shared modal dialog");
assert.match(source.orders, /FormDialog title="Create order"/, "Create Order must open in shared modal dialog");
assert.match(source.orders, /FormDialog title="Edit order"/, "Edit Order must open in shared modal dialog");
assert.match(source.shipmentsPage, /FormDialog title="Create shipment"/, "Create Shipment must open in shared modal dialog");
assert.match(source.advertising, /FormDialog title="Create campaign"/, "Create Campaign must open in shared modal dialog");
assert.match(source.advertising, /FormDialog title="Add daily metric"/, "Add Daily Metric must open in shared modal dialog");
assert.match(source.formDialog, /sellora-dialog-overlay/, "Shared form dialog must use unified overlay marker");
assert.match(source.formDialog, /sellora-dialog-panel/, "Shared form dialog must use unified panel marker");
assert.match(source.formDialog, /backdrop-blur-sm/, "Shared form dialog must use consistent backdrop blur");
assert.match(source.formDialog, /max-h-\[calc\(100dvh-1\.5rem\)\]/, "Shared form dialog must be mobile viewport safe");
assert.match(source.editDialog, /sellora-dialog-panel/, "Edit dialogs must use shared modal shell styling");
assert.match(source.confirmDialog, /sellora-dialog-panel/, "Confirm dialogs must use shared modal shell styling");
assert.match(source.shipmentsPage, /minmax\(420px,460px\)/, "Shipment details desktop panel should have readable width");
assert.match(source.shipmentDetails, /DetailRow/, "Shipment details must use structured label/value rows");
assert.match(source.shipmentDetails, /p-5|sm:p-6/, "Shipment details must have comfortable internal padding");
assert.match(source.dashboardPage, /dark:from-violet-500\/20/, "Dashboard logistics/advertising strips must use readable dark gradients");
assert.match(source.dashboardPage, /dark:text-white/, "Dashboard logistics/advertising values must be readable in dark mode");
assert.match(source.dashboardKpi, /dark:bg-slate-900/, "Dashboard KPI cards must have readable dark surfaces");
assert.match(source.dashboardKpi, /dark:text-violet-200/, "Dashboard KPI pills/icons must be readable in dark theme");
assert.match(source.recentOrders, /min-w-0 overflow-hidden/, "Recent orders must guard mobile overflow");
assert.match(source.recentOrders, /truncate/, "Recent orders must truncate long order numbers");
assert.match(source.topProducts, /min-w-0 overflow-hidden/, "Top products must guard mobile overflow");
assert.match(source.topProducts, /truncate/, "Top products must truncate long names/SKUs");
assert.match(source.advertising, /max-w-full break-words text-2xl/, "Advertising heading must wrap on mobile");
assert.match(source.advertising, /grid max-w-full min-w-0/, "Advertising page sections must constrain mobile width");
assert.match(source.orderForm, /Items subtotal/, "Order form totals block must remain present");
assert.match(source.orderForm, /dark:bg-white\/\[0\.05\]/, "Order totals block must be readable in dark mode");
assert.match(source.inventory, /w-full min-w-0 max-w-full/, "Inventory selects/controls must fit mobile width");
assert.match(source.importPage, /w-full min-w-0 max-w-full/, "Import Center controls must fit mobile width");
assert.match(source.importUpload, /w-full min-w-0 max-w-full/, "Import upload file input must fit mobile width");
assert.match(source.sheetSelector, /w-full min-w-0 max-w-full/, "Import sheet select must fit mobile width");
assert.match(source.globals, /mobile-safe-top/, "Safe-area utility must exist");
assert.match(source.globals, /sidebar-scrollbar::-webkit-scrollbar/, "Custom sidebar scrollbar styling must exist");
assert.match(source.globals, /overflow-x: hidden/, "Global styles must defend against root horizontal overflow");
assert.match(source.globals, /\.dark select,\s*\n\.dark option/, "Global native select options must be dark-mode readable");
assert.match(source.globals, /sellora-dialog-panel/, "Global dialog panel styling must exist");
assert.match(source.globals, /input,\s*\nselect,\s*\ntextarea \{/, "Global form controls must be max-width constrained");
assert.equal(source.layout.includes(".png"), false, "Current PR-compatible PWA metadata must avoid binary PNG references");
assert.equal(source.manifest.includes(".png"), false, "Current PR-compatible manifest must avoid binary PNG references");

console.log("UI responsive theme branding regression passed");
