import { mkdir, writeFile } from "node:fs/promises";
import { chromium } from "@playwright/test";

const frontendUrl = (process.env.STAGING_FRONTEND_URL || "https://sellora-web-staging.vercel.app").replace(/\/$/, "");
const apiUrl = (process.env.STAGING_API_URL || "https://sellora-api-staging.onrender.com").replace(/\/$/, "");
const ownerEmail = process.env.STAGING_OWNER_EMAIL;
const ownerPassword = process.env.STAGING_OWNER_PASSWORD;
const expectedWorkspaceId = process.env.STAGING_TEST_WORKSPACE_ID;

for (const [key, value] of Object.entries({ ownerEmail, ownerPassword, expectedWorkspaceId })) {
  if (!value) throw new Error(`Missing required runtime value: ${key}`);
}

const viewports = [
  { name: "desktop-1366", width: 1366, height: 768 },
  { name: "mobile-375", width: 375, height: 812 },
  { name: "mobile-390", width: 390, height: 844 },
  { name: "mobile-430", width: 430, height: 932 },
  { name: "tablet-768", width: 768, height: 1024 },
];

const protectedRoutes = [
  "/dashboard",
  "/leads",
  "/customers",
  "/orders",
  "/inventory",
  "/shipments",
  "/finance",
  "/advertising",
  "/analytics",
  "/settings/workspace",
];

function safePath(url) {
  try {
    const parsed = new URL(url);
    return parsed.pathname;
  } catch {
    return "unknown";
  }
}

async function loadOwnerMemberships() {
  const loginResponse = await fetch(`${apiUrl}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: ownerEmail, password: ownerPassword }),
    signal: AbortSignal.timeout(20_000),
  });
  if (!loginResponse.ok) throw new Error(`Owner API login failed with HTTP ${loginResponse.status}`);
  const tokens = await loginResponse.json();
  const meResponse = await fetch(`${apiUrl}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
    signal: AbortSignal.timeout(20_000),
  });
  if (!meResponse.ok) throw new Error(`/auth/me failed with HTTP ${meResponse.status}`);
  const me = await meResponse.json();
  const memberships = Array.isArray(me.memberships) ? me.memberships : [];
  if (!memberships.some((item) => item.workspace_id === expectedWorkspaceId)) {
    throw new Error("Synthetic OWNER does not belong to STAGING_TEST_WORKSPACE_ID");
  }
  return memberships.map((item) => ({
    workspace_id: item.workspace_id,
    workspace_name: item.workspace_name,
    role: item.role,
  }));
}

async function loginThroughUi(page, password = ownerPassword) {
  await page.goto(`${frontendUrl}/login`, { waitUntil: "domcontentloaded", timeout: 30_000 });
  await page.locator('input[type="email"]').fill(ownerEmail);
  await page.locator('input[type="password"]').fill(password);
  await page.locator('button[type="submit"]').click();
}

async function assertNoFatalUi(page) {
  const bodyText = await page.locator("body").innerText();
  for (const marker of ["Application Error", "Internal Server Error", "This page could not be found"]) {
    if (bodyText.includes(marker)) throw new Error(`Fatal UI marker detected: ${marker}`);
  }
  const overflow = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  if (overflow.scrollWidth > overflow.clientWidth + 2) {
    throw new Error(`Horizontal overflow: ${overflow.scrollWidth} > ${overflow.clientWidth}`);
  }
  return overflow;
}

async function runInvalidCredentialCheck(browser) {
  const context = await browser.newContext({ viewport: { width: 1366, height: 768 } });
  const page = await context.newPage();
  try {
    await loginThroughUi(page, `${ownerPassword}-invalid`);
    const alert = page.locator('[role="alert"]');
    await alert.waitFor({ state: "visible", timeout: 15_000 });
    if (!page.url().includes("/login")) throw new Error("Invalid credentials unexpectedly left /login");
    await page.waitForFunction(() => {
      const button = document.querySelector('button[type="submit"]');
      return button instanceof HTMLButtonElement && !button.disabled;
    }, null, { timeout: 5_000 });
    return { status: "PASS", response: "bounded-user-safe-error" };
  } finally {
    await context.close();
  }
}

async function runViewport(browser, viewport, memberships) {
  const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height } });
  await context.addInitScript((workspaceId) => {
    window.localStorage.setItem("sellora.current_workspace_id", workspaceId);
  }, expectedWorkspaceId);
  const page = await context.newPage();
  const consoleErrors = [];
  const httpErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text().slice(0, 300));
  });
  page.on("response", (response) => {
    if (response.status() >= 500) httpErrors.push({ path: safePath(response.url()), status: response.status() });
  });

  try {
    await loginThroughUi(page);
    await page.waitForURL("**/dashboard", { timeout: 30_000 });
    await page.locator("main").waitFor({ state: "visible", timeout: 20_000 });
    const selectedWorkspaceId = await page.evaluate(() => window.localStorage.getItem("sellora.current_workspace_id"));
    if (selectedWorkspaceId !== expectedWorkspaceId) throw new Error("Frontend selected the wrong workspace after login");

    const initialOverflow = await assertNoFatalUi(page);
    const result = {
      name: viewport.name,
      viewport: { width: viewport.width, height: viewport.height },
      status: "PASS",
      selected_workspace: "expected",
      overflow: initialOverflow,
      routes: [],
      workspace_switch: "not-run-on-this-viewport",
      logout: "not-run-on-this-viewport",
      console_error_count: 0,
      http_5xx_count: 0,
    };

    if (viewport.name === "desktop-1366") {
      for (const route of protectedRoutes) {
        const response = await page.goto(`${frontendUrl}${route}`, { waitUntil: "domcontentloaded", timeout: 30_000 });
        if (response && response.status() >= 400) throw new Error(`${route} returned HTTP ${response.status()}`);
        await page.locator("main").waitFor({ state: "visible", timeout: 20_000 });
        await assertNoFatalUi(page);
        result.routes.push({ route, status: "PASS" });
      }

      if (memberships.length < 2) {
        throw new Error("Workspace switching cannot be verified because the OWNER has fewer than two memberships");
      }
      const alternate = memberships.find((item) => item.workspace_id !== expectedWorkspaceId);
      await page.locator(".account-profile-trigger").click();
      const switchButton = page.locator("button", { hasText: alternate.workspace_name }).first();
      await switchButton.click();
      await page.waitForTimeout(1_000);
      const switchedWorkspaceId = await page.evaluate(() => window.localStorage.getItem("sellora.current_workspace_id"));
      if (switchedWorkspaceId !== alternate.workspace_id) throw new Error("Workspace switch did not update the active workspace");
      result.workspace_switch = "PASS";

      await page.locator(".account-profile-trigger").click();
      const logoutButton = page.locator('[role="menuitem"]').filter({ hasText: /Вийти|Log out/i }).last();
      await logoutButton.click();
      await page.waitForURL("**/login", { timeout: 15_000 });
      const storageState = await page.evaluate(() => ({
        access: window.localStorage.getItem("sellora.access_token"),
        refresh: window.localStorage.getItem("sellora.refresh_token"),
      }));
      if (storageState.access || storageState.refresh) throw new Error("Logout did not clear auth tokens");
      result.logout = "PASS";
    }

    if (consoleErrors.length) throw new Error(`Console errors detected: ${consoleErrors.join(" | ")}`);
    if (httpErrors.length) throw new Error(`HTTP 5xx responses detected: ${JSON.stringify(httpErrors)}`);
    result.console_error_count = consoleErrors.length;
    result.http_5xx_count = httpErrors.length;
    return result;
  } finally {
    await context.close();
  }
}

const memberships = await loadOwnerMemberships();
const browser = await chromium.launch({ headless: true });
const report = {
  generated_at: new Date().toISOString(),
  frontend: frontendUrl,
  backend: apiUrl,
  invalid_credentials: null,
  owner_membership_count: memberships.length,
  viewports: [],
  decision: "PASS",
};

try {
  report.invalid_credentials = await runInvalidCredentialCheck(browser);
  for (const viewport of viewports) {
    report.viewports.push(await runViewport(browser, viewport, memberships));
  }
} catch (error) {
  report.decision = "FAIL";
  report.failure = error instanceof Error ? error.message : String(error);
  throw error;
} finally {
  await browser.close();
  await mkdir("../artifacts", { recursive: true });
  await writeFile("../artifacts/staging-runtime-browser-gate.json", `${JSON.stringify(report, null, 2)}\n`, "utf8");
}

console.log(`Sellora staging browser runtime closure: ${report.decision}`);
