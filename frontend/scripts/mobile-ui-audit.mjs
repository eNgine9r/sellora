import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { chromium } from "playwright";

const baseUrl = (process.env.MOBILE_AUDIT_BASE_URL ?? "http://127.0.0.1:3000").replace(/\/$/, "");
const apiBaseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "https://sellora-api-staging.onrender.com/api/v1").replace(/\/$/, "");
const email = process.env.STAGING_OWNER_EMAIL;
const password = process.env.STAGING_OWNER_PASSWORD;
const outputRoot = path.resolve(process.cwd(), "artifacts/mobile-ui-audit");
const screenshotsRoot = path.join(outputRoot, "screenshots");
const dialogRoot = path.join(outputRoot, "dialogs");
fs.mkdirSync(screenshotsRoot, { recursive: true });
fs.mkdirSync(dialogRoot, { recursive: true });

const viewports = [
  { name: "375x812", width: 375, height: 812 },
  { name: "390x844", width: 390, height: 844 },
  { name: "430x932", width: 430, height: 932 },
];

function walkPages(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name);
    return entry.isDirectory() ? walkPages(target) : [target];
  });
}

function discoverAppRoutes() {
  const appRoot = path.join(path.resolve(path.dirname(new URL(import.meta.url).pathname), ".."), "src", "app");
  const dynamicTemplates = [];
  const routes = walkPages(appRoot)
    .filter((file) => file.endsWith(`${path.sep}page.tsx`))
    .map((file) => {
      const relativeDirectory = path.relative(appRoot, path.dirname(file)).split(path.sep).filter((segment) => !segment.startsWith("(") && !segment.startsWith("@"));
      const route = relativeDirectory.length ? `/${relativeDirectory.join("/")}` : "/";
      if (route.includes("[") || route.includes("]")) dynamicTemplates.push(route);
      return route;
    })
    .filter((route) => !route.includes("[") && !route.includes("]"));
  return { routes: [...new Set(routes)].sort(), dynamicTemplates: [...new Set(dynamicTemplates)].sort() };
}

const discovered = discoverAppRoutes();
const publicRoutes = discovered.routes.filter((route) => route === "/" || route === "/login" || route.startsWith("/legal/"));
const protectedRoutes = discovered.routes.filter((route) => !publicRoutes.includes(route));

const unsafeAction = /ТТН|видал|архів|зберег|підтверд|відправ|викон|синхрон|оновити статус/i;
const safeDialogAction = /^(створити|додати|редагувати|імпортувати|налаштувати)/i;
const report = { baseUrl, apiBaseUrl, generatedAt: new Date().toISOString(), discoveredRoutes: discovered.routes, protectedRoutes, publicRoutes, dynamicTemplates: discovered.dynamicTemplates, viewports: [], public: [], authenticated: false, fatalError: null };

function slug(route) {
  return route === "/" ? "landing" : route.replace(/^\//, "").replaceAll("/", "--") || "root";
}

function writeReport() {
  fs.writeFileSync(path.join(outputRoot, "report.json"), JSON.stringify(report, null, 2));
  const lines = [
    "# Sellora Mobile UI Audit",
    "",
    `Generated: ${report.generatedAt}`,
    `Base URL: ${baseUrl}`,
    `Authenticated: ${report.authenticated ? "yes" : "no"}`,
    report.fatalError ? `Fatal error: ${report.fatalError}` : "",
    "",
    "| Viewport | Route | Status | Horizontal overflow | Dialog |",
    "|---|---|---|---:|---|",
  ].filter(Boolean);
  for (const viewport of report.viewports) {
    for (const entry of viewport.routes) {
      lines.push(`| ${viewport.name} | \`${entry.route}\` | ${entry.status} | ${entry.overflow?.documentOverflow ?? "—"} px | ${entry.dialog ? (entry.dialog.withinViewport ? "PASS" : "OUTSIDE") : "not opened"} |`);
    }
  }
  fs.writeFileSync(path.join(outputRoot, "report.md"), `${lines.join("\n")}\n`);
}

async function fetchJson(url, init, label) {
  const response = await fetch(url, init);
  if (!response.ok) throw new Error(`${label} failed with HTTP ${response.status}`);
  return response.json();
}

async function createAuthState() {
  if (!email || !password) throw new Error("STAGING_OWNER_EMAIL and STAGING_OWNER_PASSWORD are required for protected-route audit");
  const tokens = await fetchJson(`${apiBaseUrl}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  }, "Staging login");
  const user = await fetchJson(`${apiBaseUrl}/auth/me`, {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  }, "Current user lookup");
  const workspaceId = user.memberships?.find((membership) => typeof membership.workspace_id === "string" && membership.workspace_id.trim())?.workspace_id ?? null;
  if (!workspaceId) throw new Error("Authenticated staging owner has no active workspace membership");
  return { tokens, user, workspaceId };
}

async function inspectViewport(page) {
  return page.evaluate(() => {
    const viewportWidth = window.innerWidth;
    const documentOverflow = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - viewportWidth;
    const offenders = Array.from(document.querySelectorAll("body *")).flatMap((element) => {
      const style = window.getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      if (style.display === "none" || style.visibility === "hidden" || rect.width === 0 || rect.height === 0) return [];
      if (rect.right <= viewportWidth + 1 && rect.left >= -1) return [];
      return [{
        tag: element.tagName.toLowerCase(),
        id: element.id || null,
        className: typeof element.className === "string" ? element.className.slice(0, 180) : null,
        text: (element.textContent || "").trim().replace(/\s+/g, " ").slice(0, 100),
        left: Math.round(rect.left),
        right: Math.round(rect.right),
        width: Math.round(rect.width),
      }];
    }).slice(0, 12);
    return { viewportWidth, documentOverflow: Math.max(0, Math.round(documentOverflow)), offenders };
  });
}

async function inspectDialog(page) {
  const dialog = page.locator('[role="dialog"]').last();
  if (!(await dialog.isVisible().catch(() => false))) return null;
  return dialog.evaluate((element) => {
    const panel = element.querySelector(".sellora-dialog-panel") ?? element;
    const rect = panel.getBoundingClientRect();
    const viewport = { width: window.innerWidth, height: window.innerHeight };
    return {
      left: Math.round(rect.left), top: Math.round(rect.top), right: Math.round(rect.right), bottom: Math.round(rect.bottom),
      width: Math.round(rect.width), height: Math.round(rect.height),
      withinViewport: rect.left >= -1 && rect.top >= -1 && rect.right <= viewport.width + 1 && rect.bottom <= viewport.height + 1,
      scrollWidth: panel.scrollWidth, clientWidth: panel.clientWidth,
      scrollHeight: panel.scrollHeight, clientHeight: panel.clientHeight,
      horizontalOverflow: Math.max(0, panel.scrollWidth - panel.clientWidth),
    };
  });
}

async function openSafeDialog(page, routeName, viewportName) {
  const buttons = page.locator("button:visible");
  const count = Math.min(await buttons.count(), 80);
  for (let index = 0; index < count; index += 1) {
    const button = buttons.nth(index);
    const text = (await button.innerText().catch(() => "")).trim().replace(/\s+/g, " ");
    if (!safeDialogAction.test(text) || unsafeAction.test(text)) continue;
    if (await button.isDisabled().catch(() => true)) continue;
    await button.click({ timeout: 3000 }).catch(() => null);
    await page.waitForTimeout(350);
    const metrics = await inspectDialog(page);
    if (!metrics) continue;
    const file = path.join(dialogRoot, viewportName, `${routeName}.png`);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    await page.screenshot({ path: file, fullPage: false });
    await page.keyboard.press("Escape").catch(() => null);
    return { trigger: text, screenshot: path.relative(outputRoot, file), ...metrics };
  }
  return null;
}

const browser = await chromium.launch({ headless: true, args: ["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"] });
try {
  const publicContext = await browser.newContext({ viewport: viewports[0] });
  const publicPage = await publicContext.newPage();
  publicPage.setDefaultTimeout(20_000);
  for (const publicRoute of publicRoutes) {
    await publicPage.goto(`${baseUrl}${publicRoute}`, { waitUntil: "domcontentloaded", timeout: 60_000 });
    await publicPage.waitForTimeout(500);
    const file = path.join(screenshotsRoot, "public", `${slug(publicRoute)}.png`);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    await publicPage.screenshot({ path: file, fullPage: true });
    report.public.push({ route: publicRoute, screenshot: path.relative(outputRoot, file), ...(await inspectViewport(publicPage)) });
  }
  await publicContext.close();

  const authState = await createAuthState();
  const context = await browser.newContext({ viewport: viewports[0] });
  await context.addInitScript(({ tokens, user, workspaceId }) => {
    window.localStorage.setItem("sellora.access_token", tokens.access_token);
    window.localStorage.setItem("sellora.refresh_token", tokens.refresh_token);
    window.localStorage.setItem("sellora.current_user", JSON.stringify(user));
    window.localStorage.setItem("sellora.current_workspace_id", workspaceId);
  }, authState);
  const page = await context.newPage();
  page.setDefaultTimeout(20_000);
  await page.goto(`${baseUrl}/dashboard`, { waitUntil: "domcontentloaded", timeout: 60_000 });
  await page.waitForFunction(() => window.location.pathname !== "/login", null, { timeout: 30_000 });
  report.authenticated = true;

  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    const viewportReport = { ...viewport, routes: [] };
    for (const route of protectedRoutes) {
      const routeName = slug(route);
      const entry = { route, status: "PASS", screenshot: null, overflow: null, dialog: null, error: null };
      try {
        const response = await page.goto(`${baseUrl}${route}`, { waitUntil: "domcontentloaded", timeout: 60_000 });
        await page.waitForTimeout(800);
        entry.httpStatus = response?.status() ?? null;
        entry.finalUrl = page.url().replace(baseUrl, "");
        const file = path.join(screenshotsRoot, viewport.name, `${routeName}.png`);
        fs.mkdirSync(path.dirname(file), { recursive: true });
        await page.screenshot({ path: file, fullPage: true });
        entry.screenshot = path.relative(outputRoot, file);
        entry.overflow = await inspectViewport(page);
        entry.dialog = await openSafeDialog(page, routeName, viewport.name);
        if (entry.overflow.documentOverflow > 1 || entry.overflow.offenders.length > 0 || (entry.dialog && (!entry.dialog.withinViewport || entry.dialog.horizontalOverflow > 1))) entry.status = "ISSUE";
      } catch (error) {
        entry.status = "ERROR";
        entry.error = error instanceof Error ? error.message.slice(0, 500) : String(error);
      }
      viewportReport.routes.push(entry);
    }
    report.viewports.push(viewportReport);
    writeReport();
  }

  const issues = report.viewports.flatMap((viewport) => viewport.routes).filter((entry) => entry.status !== "PASS");
  console.log(`Mobile UI audit complete: ${report.viewports.length} viewports, ${routes.length} protected routes, ${issues.length} entries need review.`);
} catch (error) {
  report.fatalError = error instanceof Error ? error.message.slice(0, 800) : String(error);
  writeReport();
  throw error;
} finally {
  await browser.close();
}
