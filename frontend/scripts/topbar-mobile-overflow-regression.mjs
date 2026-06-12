import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const files = {
  topbar: "frontend/src/components/app-topbar.tsx",
  themeToggle: "frontend/src/components/theme-toggle.tsx",
  advertising: "frontend/src/app/advertising/page.tsx",
  adKpi: "frontend/src/features/advertising/components/advertising-kpi-card.tsx",
  adFilter: "frontend/src/features/advertising/components/advertising-date-range-filter.tsx",
  adCampaignForm: "frontend/src/features/advertising/components/campaign-form.tsx",
  adMetricForm: "frontend/src/features/advertising/components/ad-metric-form.tsx",
  adCampaignTable: "frontend/src/features/advertising/components/campaign-table.tsx",
  adMetricTable: "frontend/src/features/advertising/components/ad-metric-table.tsx",
  importPage: "frontend/src/app/settings/import/page.tsx",
  importUpload: "frontend/src/features/import-center/components/import-upload-card.tsx",
  importPreview: "frontend/src/features/import-center/components/import-preview-table.tsx",
  importLogs: "frontend/src/features/import-center/components/import-logs-table.tsx",
  importValidationIssues: "frontend/src/features/import-center/components/validation-issues-table.tsx",
  globals: "frontend/src/app/globals.css",
};

const source = Object.fromEntries(Object.entries(files).map(([key, path]) => [key, readFileSync(path, "utf8")]));

assert.match(source.topbar, /relative hidden min-w-\[220px\] flex-1/, "Topbar search must be flex-safe and min-width constrained");
assert.match(source.topbar, /lg:max-w-\[520px\]/, "Topbar search should have a stable desktop max width");
assert.doesNotMatch(source.topbar, /DateRangeSelector/, "Shared topbar must not render the duplicated global period selector");
assert.match(source.topbar, /items-center gap-1 whitespace-nowrap/, "Create button text and arrow must stay on one line");
assert.match(source.topbar, /overflow-x-hidden/, "Topbar container must not create horizontal overflow");
assert.match(source.themeToggle, /shrink-0/, "Theme toggle must align as a fixed-size topbar control");

assert.match(source.advertising, /sellora-mobile-page/, "Advertising page must use mobile-safe page wrapper");
assert.match(source.advertising, /w-full max-w-full min-w-0/, "Advertising page sections must be width constrained");
assert.match(source.advertising, /break-words text-2xl/, "Advertising title must wrap on mobile");
assert.match(source.advertising, /whitespace-normal/, "Advertising action buttons must not clip text on mobile");
assert.match(source.adKpi, /w-full min-w-0 max-w-full overflow-hidden/, "Advertising KPI cards must fit mobile width");
assert.match(source.adFilter, /w-full min-w-0 max-w-full/, "Advertising filters must fit mobile width");
assert.match(source.adCampaignForm, /w-full min-w-0 max-w-full/, "Campaign form controls must fit mobile width");
assert.match(source.adMetricForm, /w-full min-w-0 max-w-full/, "Daily metric form controls must fit mobile width");
assert.match(source.adCampaignTable, /max-w-full overflow-x-auto/, "Campaign table must scroll internally");
assert.match(source.adMetricTable, /max-w-full overflow-x-auto/, "Metric table must scroll internally");

assert.match(source.importPage, /sellora-mobile-page/, "Import Center page must use mobile-safe page wrapper");
assert.match(source.importPage, /truncate rounded-lg/, "Import preset select must truncate long preset names");
assert.match(source.importPage, /whitespace-normal/, "Import action buttons must stack/wrap safely on mobile");
assert.match(source.importUpload, /sr-only/, "Import upload must use custom mobile-safe file picker");
assert.match(source.importUpload, /truncate/, "Import upload filename must truncate instead of widening the page");
assert.match(source.importPreview, /max-w-full overflow-x-auto/, "Import preview table must scroll internally");
assert.match(source.importLogs, /max-w-full overflow-x-auto/, "Import logs table must scroll internally");
assert.match(source.importValidationIssues, /max-w-full overflow-x-auto/, "Import validation table must scroll internally");
assert.match(source.globals, /sellora-mobile-page/, "Global mobile overflow guard classes must exist");

for (const [name, text] of Object.entries({ advertising: source.advertising, importPage: source.importPage })) {
  assert.doesNotMatch(text, /w-screen|min-w-\[(?:6|7|8|9)\d{2}px\]/, `${name} must not use nested w-screen or oversized fixed mobile widths`);
}

console.log("Topbar mobile overflow regression passed");
