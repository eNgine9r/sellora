import { readFileSync } from "node:fs";

const read = (path) => readFileSync(path, "utf8");
const config = read("frontend/next.config.ts");
const auth = read("frontend/src/services/auth.service.ts");
const store = read("frontend/src/stores/auth.store.tsx");
const api = read("frontend/src/services/api.ts");
const shell = read("frontend/src/components/app-shell.tsx");

const checks = [
  ["same-origin API rewrite", config.includes('source: API_PATH + "/:path*"') && config.includes('destination: upstream + "/:path*"')],
  ["upstream is server-configured", config.includes("SELLORA_API_UPSTREAM_URL") && config.includes("NEXT_PUBLIC_API_BASE_URL")],
  ["browser uses same-origin route", config.includes('env: { NEXT_PUBLIC_API_BASE_URL: API_PATH }')],
  ["secure cookie mode for exact staging hostname", auth.includes('hosts.includes(window.location.hostname.toLowerCase())')],
  ["session login", auth.includes('"/auth/session/login"') && auth.includes('credentials: "same-origin"')],
  ["session refresh with HttpOnly cookie", auth.includes('/auth/session/refresh') && auth.includes('credentials: "same-origin"')],
  ["server-side logout", auth.includes('/auth/session/logout') && store.includes("await revokeCookieSession()")],
  ["access token never persisted in secure mode", auth.includes("memoryAccessToken = tokens.access_token") && auth.includes("window.localStorage.removeItem(ACCESS_TOKEN_KEY)")],
  ["restore secured session on refresh", store.includes("await reloadCurrentUser()") && store.includes("await refreshCookieSession()")],
  ["regular API retry can refresh cookie", api.includes("COOKIE_SESSION_AUTH_ENABLED") && api.includes('refreshAccessToken(refreshToken ?? "")')],
  ["logout waits for revocation", shell.includes("await logout()")],
];
const failed = checks.filter(([, passed]) => !passed);
for (const [name, passed] of checks) console.log((passed ? "PASS" : "FAIL") + " " + name);
if (failed.length) process.exit(1);
