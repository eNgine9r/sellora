import { readFileSync } from "node:fs";

const appShell = readFileSync("frontend/src/components/app-shell.tsx", "utf8");
const topbar = readFileSync("frontend/src/components/app-topbar.tsx", "utf8");
const liveProvider = readFileSync("frontend/src/components/direct-live-provider.tsx", "utf8");
const directPage = readFileSync("frontend/src/app/direct/page.tsx", "utf8");
const directService = readFileSync("frontend/src/services/direct.ts", "utf8");
const sidebar = readFileSync("frontend/src/components/app-sidebar.tsx", "utf8");
const uk = readFileSync("frontend/src/i18n/messages/uk.json", "utf8");
const en = readFileSync("frontend/src/i18n/messages/en.json", "utf8");

const protectedRoutesBlock = appShell.match(/const protectedRoutes = \[[\s\S]*?\];/)?.[0] ?? "";
const mobileQuickNavBlock = appShell.match(/const mobileQuickNav = \[[\s\S]*?\];/)?.[0] ?? "";
const checks = [
  ["/direct is in canonical protected routes", protectedRoutesBlock.includes('"/direct"')],
  ["unauthenticated protected route redirects to login", appShell.includes('router.replace("/login")') && appShell.includes('status === "unauthenticated"')],
  ["authenticated protected content renders inside AppShell", appShell.includes("<AppSidebar showBrand={false} />") && appShell.includes("<AppTopbar") && appShell.includes("{children}")],
  ["mobile navigation drawer remains canonical", appShell.includes("mobile-sidebar-drawer") && appShell.includes("<AppSidebar onNavigate")],
  ["Direct is available in mobile quick nav", mobileQuickNavBlock.includes('href: "/direct"') && mobileQuickNavBlock.includes('labelKey: "navigation.direct"')],
  ["Direct sidebar item exists and supports nested active state", sidebar.includes('["/direct", "navigation.direct"') && sidebar.includes('pathname.startsWith(`${href}/`)')],
  ["Direct page uses WorkspacePage instead of standalone min-h-screen shell", directPage.includes("<WorkspacePage") && !directPage.includes("min-h-screen") && !directPage.includes("<main")],
  ["Direct page does not use viewport width override", !directPage.includes("100vw") && !directPage.includes("w-screen")],
  ["Direct page exposes distinct AI drawer state", directPage.includes("aiPanelOpen") && directPage.includes("setAiPanelOpen") && directPage.includes("data-direct-ai-panel")],
  ["Direct page keeps AI draft safety copy", directPage.includes("direct.noAutoSend") && uk.includes("Чернетки AI не відправляються")],
  ["Ukrainian and English Direct navigation labels exist", uk.includes('"direct": "Direct"') && en.includes('"direct": "Direct"')],
  ["protected AppShell installs Direct live provider", appShell.includes("<DirectLiveProvider") && liveProvider.includes('refetchInterval: 2000')],
  ["live provider invalidates dialog and message queries", liveProvider.includes('"direct-conversations"') && liveProvider.includes('"direct-messages"')],
  ["browser and in-app notifications remain user controlled", liveProvider.includes("Notification.requestPermission") && liveProvider.includes("data-direct-live-toast")],
  ["topbar notification bell shows unread and order intent signals", topbar.includes("data-direct-notification-bell") && topbar.includes("Ймовірне замовлення")],
  ["Direct conversations and messages refresh without page reload", directPage.includes('refetchInterval: 2000') && directPage.includes('refetchInterval: 1500')],
  ["opening a conversation marks it read", directPage.includes("markDirectConversationRead") && directService.includes("/read")],
];
let failed = false;
for (const [label, ok] of checks) {
  if (!ok) {
    console.error(`Direct AppShell regression failed: ${label}`);
    failed = true;
  }
}
if (failed) process.exit(1);
console.log(`Direct AppShell regression passed (${checks.length} checks).`);
