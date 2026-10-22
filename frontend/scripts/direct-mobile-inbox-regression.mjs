import { readFileSync } from "node:fs";

const direct = readFileSync("frontend/src/app/direct/page.tsx", "utf8");
const css = readFileSync("frontend/src/app/globals.css", "utf8");

const checks = [
  ["mobile inbox and thread separated", direct.includes('threadOpenOnMobile ? "hidden min-w-0 lg:block"') && direct.includes('threadOpenOnMobile ? "min-w-0" : "hidden min-w-0 lg:block"')],
  ["thread returns to list", direct.includes('const handleBackToInbox') && direct.includes("onBack={handleBackToInbox}") && direct.includes('aria-label="Назад до діалогів"')],
  ["URL selection is deep-link and browser-back safe", direct.includes("useSearchParams().get") && direct.includes("router.push(") && direct.includes("router.replace(\"/direct\"")],
  ["restore scroll position", direct.includes("listScrollPosition.current = window.scrollY") && direct.includes("window.scrollTo(0, listScrollPosition.current)")],
  ["initial batch is bounded", direct.includes("DIRECT_INBOX_BATCH_SIZE = 20") && direct.includes("filteredConversations.slice(0, visibleCount)")],
  ["intersection auto-loads additional batches", direct.includes("new IntersectionObserver") && direct.includes("data-direct-load-sentinel")],
  ["manual load-more accessible fallback", direct.includes("Завантажити ще") && direct.includes("setVisibleCount((count) => count + DIRECT_INBOX_BATCH_SIZE)")],
  ["search is functional", direct.includes("value={search}") && direct.includes("setSearch(event.target.value)") && direct.includes("toLocaleLowerCase().includes(term)")],
  ["filter chips are functional", direct.includes('filter === "unread"') && direct.includes('filter === "orders"') && direct.includes("aria-pressed={filter === key}")],
  ["thread presents messages at top", direct.includes("data-direct-mobile-thread") && direct.includes("data-direct-mobile-details") && direct.includes("min-h-0 flex-1 space-y-3")],
  ["iPhone thread fits viewport", css.includes(".direct-mobile-thread") && css.includes("100dvh") && css.includes("safe-area-inset-bottom")],
  ["mobile PWA header is opaque", css.includes(".mobile-safe-top[data-shell-topbar]") && css.includes("-webkit-backdrop-filter: none !important") && css.includes("background-color: var(--canvas)")],
  ["desktop remains three-panel", direct.includes("lg:grid-cols-[minmax(260px,320px)_minmax(0,1fr)_minmax(320px,380px)]")],
];
const failures = checks.filter(([, ok]) => !ok);
for (const [name, ok] of checks) console.log(`${ok ? "PASS" : "FAIL"} ${name}`);
if (failures.length) process.exit(1);
