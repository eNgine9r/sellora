import { readFileSync } from "node:fs";

const checks = [];
const read = (path) => readFileSync(path, "utf8");
const has = (path, ...needles) => needles.every((needle) => read(path).includes(needle));
const notHas = (path, needle) => !read(path).includes(needle);
const check = (label, condition) => checks.push({ label, condition });

check("standard feedback modal/drawer portal", has("frontend/src/components/feedback-dialog.tsx", "createPortal", "feedback-modal", "z-[80]", "sm:items-center", "overscroll-contain"));
check("modal overlay and sticky actions", has("frontend/src/components/feedback-dialog.tsx", "bg-slate-950/55", "sticky bottom-0", "feedback.form.privacyHint"));
check("mobile sidebar compact footer", has("frontend/src/components/app-shell.tsx", "mobile-sidebar-footer-compact", "truncate", "mobileSidebar.quickControls"));
check("mobile More menu safe positioning", has("frontend/src/components/app-topbar.tsx", "fixed right-3", "z-[61]", "max-h-[min(70vh,420px)]", "mobileMoreMenu.close"));
check("calendar icon visibility styles", has("frontend/src/app/globals.css", "::-webkit-calendar-picker-indicator", "color-scheme: dark", "sellora-date-input"));
check("analytics pagination", has("frontend/src/app/analytics/page.tsx", "analytics-pagination-section", "PaginationControls", "paginatedSalesRows", "setAnalyticsPage(1)"));
check("analytics page size 5/15/30", has("frontend/src/app/analytics/page.tsx", "useState<(typeof PAGE_SIZE_OPTIONS)[number]>(5)") && has("frontend/src/components/pagination-controls.tsx", "PAGE_SIZE_OPTIONS = [5, 15, 30]"));
check("period selector removed from shared topbar", notHas("frontend/src/components/app-topbar.tsx", "DateRangeSelector"));
check("local period selector preserved", has("frontend/src/app/dashboard/page.tsx", "DateRangeSelector compact") && has("frontend/src/app/analytics/page.tsx", "DateRangeSelector compact"));
check("topbar button style normalization", has("frontend/src/components/app-topbar.tsx", "topbar-action", "mobile-topbar-compact") && has("frontend/src/components/feedback-dialog.tsx", "topbar-action inline-flex h-12"));
check("reports sidebar route", has("frontend/src/app/reports/page.tsx", "redirect(\"/analytics\")") && has("frontend/src/components/app-sidebar.tsx", 'href === "/reports" && pathname === "/analytics"'));
check("i18n keys", ["en", "uk"].every((locale) => has(`frontend/src/i18n/messages/${locale}.json`, "feedback", "mobileTopbar", "mobileSidebar", "mobileMoreMenu", "calendarInput", "reports", "analytics", "pagination", "actions")));
check("responsive QA docs", has("docs/staging-qa-checklist.md", "Analytics detailed sales table pagination", "Shared topbar global period selector") && has("docs/pilot-qa-checklist.md", "Re-test Analytics detailed table pagination") && has("docs/mvp-readiness.md", "Sprint 2.9 follow-up checklist"));

const failed = checks.filter((item) => !item.condition);
for (const item of checks) console.log(`${item.condition ? "✓" : "✗"} ${item.label}`);
if (failed.length) {
  console.error(`Responsive feedback analytics cleanup regression failed: ${failed.map((item) => item.label).join(", ")}`);
  process.exit(1);
}
console.log("Responsive feedback analytics cleanup regression passed.");
