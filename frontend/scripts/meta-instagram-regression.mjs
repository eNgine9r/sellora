import { readFileSync } from "node:fs";
const settingsPage = readFileSync("frontend/src/app/settings/integrations/instagram/page.tsx", "utf8");
const service = readFileSync("frontend/src/services/meta-instagram.ts", "utf8");
const directService = readFileSync("frontend/src/services/direct.ts", "utf8");
const directPage = readFileSync("frontend/src/app/direct/page.tsx", "utf8");
const checks = [
  ["Instagram settings route exists", settingsPage.includes("InstagramIntegrationPage") && settingsPage.includes("startInstagramConnect")],
  ["Instagram frontend uses backend API only", service.includes("/integrations/instagram/status") && !service.includes("META_APP_SECRET") && !service.includes("access_token")],
  ["Direct reply prepare/send services exist", directService.includes("reply/prepare") && directService.includes("reply/send") && directService.includes("Idempotency-Key")],
  ["Direct production page still has no Instagram send button", !directPage.includes("Send Instagram") && !directPage.includes("Відправити в Instagram")],
  ["Instagram settings warns by role", settingsPage.includes("canManage") && settingsPage.includes("readOnly")],
];
let failed = false;
for (const [label, ok] of checks) { if (!ok) { console.error(`Meta Instagram regression failed: ${label}`); failed = true; } }
if (failed) process.exit(1);
console.log(`Meta Instagram regression passed (${checks.length} checks).`);
