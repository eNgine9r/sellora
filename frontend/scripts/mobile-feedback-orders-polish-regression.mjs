import { readFileSync } from "node:fs";

const checks = [];
function read(path) { return readFileSync(path, "utf8"); }
function check(label, condition) { checks.push({ label, condition }); }
function has(path, ...needles) { const source = read(path); return needles.every((needle) => source.includes(needle)); }

check("mobile sidebar footer compact layout", has("frontend/src/components/app-shell.tsx", "mobile-sidebar-footer-compact", "truncate", "mobileSidebar.quickControls"));
check("mobile topbar action consolidation", has("frontend/src/components/app-topbar.tsx", "mobile-topbar-compact", "mobile-more-sheet", "MoreHorizontal", "md:hidden"));
check("mobile More menu contains feedback/language/theme", has("frontend/src/components/app-topbar.tsx", "FeedbackDialog", "LanguageSwitcher compact", "ThemeToggle compact"));
check("date range mobile overflow fix", has("frontend/src/components/date-range-selector.tsx", "date-range-mobile-custom", "grid min-w-0 gap-2", "sm:flex"));
check("calendar icon visibility styles", has("frontend/src/app/globals.css", "::-webkit-calendar-picker-indicator", "color-scheme: dark", "sellora-date-input"));
check("standard feedback modal/drawer", has("frontend/src/components/feedback-dialog.tsx", "feedback-modal", "z-[80]", "items-end", "sm:items-center", "overscroll-contain"));
check("reports sidebar route alias", has("frontend/src/components/app-sidebar.tsx", 'href === "/reports" && pathname === "/analytics"') && has("frontend/src/app/reports/page.tsx", 'redirect("/analytics")'));
check("orders pagination default and options", has("frontend/src/app/orders/page.tsx", "useState<(typeof PAGE_SIZE_OPTIONS)[number]>(5)", "PaginationControls", "paginateItems") && has("frontend/src/components/pagination-controls.tsx", "PAGE_SIZE_OPTIONS = [5, 15, 30]"));
check("orders search/filter/sort reset pagination", has("frontend/src/app/orders/page.tsx", "setPage(1);", "[search, status, paymentStatus, orderSort, pageSize]"));
check("orders empty and filtered-empty states", has("frontend/src/app/orders/page.tsx", "filteredEmptyTitle", "emptyTitle", "ordersQuery.isLoading"));
check("i18n keys", ["en", "uk"].every((locale) => has(`frontend/src/i18n/messages/${locale}.json`, "mobileTopbar", "mobileSidebar", "\"mobile\"", "\"modal\"", "\"reports\"", "\"pagination\"")));
check("responsive QA docs", has("docs/staging-qa-checklist.md", "Sprint 2.9", "Mobile sidebar footer", "Orders pagination") && has("docs/pilot-qa-checklist.md", "Sprint 2.9 Pilot QA Addendum") && has("docs/mvp-readiness.md", "Sprint 2.9 readiness update"));
check("privacy guardrails remain present", has("docs/known-limitations.md", "Instagram Direct API") && !has("frontend/src/components/feedback-dialog.tsx", "Authorization: Bearer", "Workspace ID:"));

const failed = checks.filter((item) => !item.condition);
for (const item of checks) console.log(`${item.condition ? "✓" : "✗"} ${item.label}`);
if (failed.length) {
  console.error(`Mobile feedback/orders polish regression failed: ${failed.map((item) => item.label).join(", ")}`);
  process.exit(1);
}
console.log("Mobile feedback/orders polish regression passed.");
