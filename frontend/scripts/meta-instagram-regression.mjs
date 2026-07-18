import { existsSync, readFileSync } from "node:fs";
const root = existsSync("frontend/src") ? "frontend/" : "";
const read = (path) => readFileSync(`${root}${path}`, "utf8");
const settingsPage = read("src/app/settings/integrations/instagram/page.tsx");
const hubPage = read("src/app/settings/integrations/page.tsx");
const settingsOverview = read("src/app/settings/page.tsx");
const instagramCard = read("src/features/integrations/components/instagram-messaging-integration-card.tsx");
const service = read("src/services/meta-instagram.ts");
const directService = read("src/services/direct.ts");
const directPage = read("src/app/direct/page.tsx");
const callbackPage = read("src/app/settings/integrations/instagram/callback/page.tsx");
const uk = read("src/i18n/messages/uk.json");
const checks = [
  ["Instagram settings route exists", settingsPage.includes("InstagramIntegrationPage") && settingsPage.includes("startInstagramConnect")],
  ["Instagram frontend uses backend API only", service.includes("/integrations/instagram/status") && !service.includes("META_APP_SECRET") && !service.includes("access_token")],
  ["Integration Hub includes dedicated Instagram Direct card", hubPage.includes("InstagramMessagingIntegrationCard") && instagramCard.includes("instagramSettings.hub.title")],
  ["Instagram Direct is separate from Meta Ads", hubPage.lastIndexOf("<InstagramMessagingIntegrationCard") < hubPage.lastIndexOf("<NovaPoshtaSettingsCard") && hubPage.lastIndexOf("<MetaAdsReadinessCard") > hubPage.lastIndexOf("<NovaPoshtaSettingsCard")],
  ["Instagram status query is workspace scoped", instagramCard.includes('["instagram-connection-status", workspaceId]') && settingsPage.includes('["instagram-connection-status", workspaceId]') && settingsOverview.includes('["instagram-connection-status", workspaceId]')],
  ["Instagram card exposes safe owner actions", instagramCard.includes("startInstagramConnect") && instagramCard.includes("validateInstagramConnection") && instagramCard.includes("disconnectInstagram") && instagramCard.includes("window.confirm")],
  ["Instagram card routes to settings and Direct", instagramCard.includes('href="/settings/integrations/instagram"') && instagramCard.includes('href="/direct"')],
  ["Callback clears code/state from browser history", callbackPage.includes("window.history.replaceState") && !callbackPage.includes("params.get(\"code\")") && !callbackPage.includes("params.get(\"state\")")],
  ["Callback uses safe localized statuses", callbackPage.includes("safeStatuses") && callbackPage.includes("profile_failed") && callbackPage.includes("instagramSettings.callback.status")],
  ["Ukrainian localization includes Instagram card and callback copy", uk.includes("Отримуйте повідомлення Instagram") && uk.includes("Не вдалося перевірити профіль Instagram")],
  ["Direct reply prepare/send services exist", directService.includes("reply/prepare") && directService.includes("reply/send") && directService.includes("Idempotency-Key")],
  ["Direct production page has no hardcoded sample conversations", !directPage.includes("@olena.shop") && !directPage.includes("@ira_style") && !directPage.includes("conversations = [")],
  ["Direct production page still has no uncontrolled Instagram send button", !directPage.includes("Send Instagram") && !directPage.includes("Відправити в Instagram")],
  ["Operation reconciliation service marker exists", directService.includes("reconcileMessageOperation") && directService.includes("message-operations")],
];
let failed = false;
for (const [label, ok] of checks) { if (!ok) { console.error(`Meta Instagram regression failed: ${label}`); failed = true; } }
if (failed) process.exit(1);
console.log(`Meta Instagram regression passed (${checks.length} checks).`);
