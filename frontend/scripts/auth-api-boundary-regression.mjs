import { readFileSync } from "node:fs";

const authService = readFileSync("frontend/src/services/auth.service.ts", "utf8");
const loginPage = readFileSync("frontend/src/app/login/page.tsx", "utf8");
const uk = readFileSync("frontend/src/i18n/messages/uk.json", "utf8");
const en = readFileSync("frontend/src/i18n/messages/en.json", "utf8");

const checks = [
  ["API base URL config exists", authService.includes("NEXT_PUBLIC_API_BASE_URL") && authService.includes("API_BASE_URL")],
  ["login endpoint path exists", authService.includes("/auth/login")],
  ["no localhost fallback in production-facing client", authService.includes('process.env.NODE_ENV === "production" ? "/api/v1" : DEV_API_BASE_URL')],
  ["network error type exists", authService.includes("AuthNetworkError") && loginPage.includes("auth.networkError")],
  ["invalid credentials copy differs", authService.includes("InvalidCredentialsError") && loginPage.includes("auth.invalidCredentials")],
  ["Ukrainian network copy exists", uk.includes("Не вдалося підключитися до сервера")],
  ["English network copy exists", en.includes("Could not connect to the server")],
];
let failed = false;
for (const [label, ok] of checks) {
  if (!ok) {
    console.error(`Auth API boundary regression failed: ${label}`);
    failed = true;
  }
}
if (failed) process.exit(1);
console.log(`Auth API boundary regression passed (${checks.length} checks).`);
