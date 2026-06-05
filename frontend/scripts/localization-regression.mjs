import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";

const read = (path) => readFileSync(path, "utf8");
const mustExist = (path) => assert.ok(existsSync(path), `${path} must exist`);

const files = {
  uk: "frontend/src/i18n/messages/uk.json",
  en: "frontend/src/i18n/messages/en.json",
  config: "frontend/src/i18n/config.ts",
  provider: "frontend/src/i18n/provider.tsx",
  switcher: "frontend/src/components/language-switcher.tsx",
  statusHelper: "frontend/src/i18n/status.ts",
  layout: "frontend/src/app/layout.tsx",
  sidebar: "frontend/src/components/app-sidebar.tsx",
  topbar: "frontend/src/components/app-topbar.tsx",
  dashboard: "frontend/src/app/dashboard/page.tsx",
  orders: "frontend/src/app/orders/page.tsx",
  inventory: "frontend/src/features/inventory/components/inventory-table.tsx",
  advertising: "frontend/src/app/advertising/page.tsx",
  settings: "frontend/src/app/settings/page.tsx",
  importCenter: "frontend/src/app/settings/import/page.tsx",
  payloadBuilders: "frontend/src/lib/payload-builders.ts",
  themeToggle: "frontend/src/components/theme-toggle.tsx",
};

Object.values(files).forEach(mustExist);
const source = Object.fromEntries(Object.entries(files).map(([key, path]) => [key, read(path)]));
const uk = JSON.parse(source.uk);
const en = JSON.parse(source.en);

assert.equal(uk.navigation.dashboard, "Панель", "Ukrainian navigation dictionary must be populated");
assert.equal(en.navigation.dashboard, "Dashboard", "English navigation dictionary must be populated");
assert.match(source.config, /defaultLocale = "uk"/, "Default locale must be Ukrainian");
assert.match(source.config, /localeStorageKey = "sellora_locale"/, "Locale persistence key must be stable");
assert.match(source.provider, /localStorage\.getItem\(localeStorageKey\)/, "Locale provider must read persisted language");
assert.match(source.provider, /localStorage\.setItem\(localeStorageKey, locale\)/, "Locale provider must persist selected language");
assert.match(source.switcher, /LanguageSwitcher/, "Language switcher component must exist");
assert.match(source.switcher, /locales\.map/, "Language switcher must expose supported locales");
assert.match(source.layout, /<LocaleProvider>/, "Root layout must wrap the app in LocaleProvider");
assert.match(source.layout, /<html lang="uk"/, "Initial document language must default to Ukrainian");
assert.match(source.statusHelper, /formatEnumStatus/, "Status translation helper must exist");
assert.match(source.provider, /formatStatus/, "Runtime enum status display formatter must exist");
assert.match(source.payloadBuilders, /status: values\.status|payment_status|order_status|ShipmentCreatePayload/, "Payload builders must continue to submit backend enum fields");
assert.doesNotMatch(source.payloadBuilders, /Новий|Доставлено|Оплачено|Низький залишок/, "Payload builders must not contain translated enum values");

for (const key of ["sidebar", "topbar", "dashboard", "orders", "inventory", "advertising", "settings", "importCenter"]) {
  assert.match(source[key], /useI18n|formatStatus|t\(/, `${key} must use localization hooks/helpers`);
}

assert.match(source.topbar, /LanguageSwitcher compact/, "Topbar must include compact language switcher");
assert.match(source.settings, /<LanguageSwitcher \/>/, "Settings page must include language section switcher");
assert.match(source.sidebar, /navigation\.dashboard/, "Sidebar must use navigation translation keys");
assert.match(source.topbar, /topbar\.searchPlaceholder/, "Topbar search placeholder must be translated");
assert.match(source.orders, /orders\.create|orders\.edit/, "Orders page must use order translation keys");
assert.match(source.inventory, /inventory\.lowStock|inventory\.healthy/, "Inventory badges must use translated labels");
assert.match(source.advertising, /advertising\.manualDashboard|advertising\.createCampaign/, "Advertising page must use advertising translation keys");
assert.match(source.importCenter, /importCenter\.preset|importCenter\.executeImport/, "Import Center must use import translation keys");
assert.match(source.themeToggle, /theme\.label/, "Theme labels must remain localized");
assert.match(source.topbar, /min-w-\[220px\] flex-1/, "Topbar responsive marker must remain intact");
assert.match(read("frontend/src/app/globals.css"), /sellora-scrollbar/, "Responsive scrollbar utility must remain intact");

console.log("Localization regression passed");
