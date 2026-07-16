#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const BASE_URL = process.env.STAGING_FRONTEND_URL;
const OWNER_EMAIL = process.env.STAGING_OWNER_EMAIL;
const OWNER_PASSWORD = process.env.STAGING_OWNER_PASSWORD;
const WORKSPACE_ID = process.env.QA8E_WORKSPACE_ID;
const OUT_DIR = path.resolve("artifacts/sprint-8e/browser-matrix");
const REPORT_PATH = path.resolve("artifacts/sprint-8e/browser-matrix.json");

const viewports = [
  { name: "desktop-1366x768", width: 1366, height: 768 },
  { name: "mobile-375x812", width: 375, height: 812 },
  { name: "mobile-390x844", width: 390, height: 844 },
  { name: "mobile-430x932", width: 430, height: 932 },
  { name: "tablet-768x1024", width: 768, height: 1024 },
];

const protectedRoutes = ["/dashboard", "/orders", "/inventory", "/shipments"];
const fatalMarkers = [
  "Application error",
  "Internal Server Error",
  "This page could not be found",
  "404: This page could not be found",
];
const loadingMarkers = [
  "Завантаження панелі",
  "Завантаження замовлень",
  "Завантаження відправлень",
  "Завантажуємо відправлення",
  "Завантаження реклами",
  "dashboard.loading.inventory",
];

function safeMessage(value) {
  return String(value || "")
    .replaceAll(OWNER_EMAIL || "__never__", "[EMAIL]")
    .replace(/Bearer\s+\S+/gi, "Bearer [REDACTED]")
    .replace(/\beyJ[A-Za-z0-9._-]{20,}\b/g, "[TOKEN]")
    .slice(0, 500);
}

function addCheck(target, name, ok, detail = undefined) {
  const check = { name, status: ok ? "PASS" : "FAIL" };
  if (detail !== undefined) check.detail = detail;
  target.checks.push(check);
}

async function pageState(page) {
  const bodyText = await page.locator("body").innerText().catch(() => "");
  const layout = await page.evaluate(() => ({
    viewportWidth: window.innerWidth,
    documentWidth: document.documentElement.scrollWidth,
    bodyWidth: document.body?.scrollWidth || 0,
    mainPresent: Boolean(document.querySelector("main")),
  }));
  return {
    bodyText,
    layout,
    fatalMarkers: fatalMarkers.filter((marker) => bodyText.includes(marker)),
    loadingMarkers: loadingMarkers.filter((marker) => bodyText.includes(marker)),
    currentUrl: page.url(),
  };
}

async function waitForSettledRoute(page) {
  await page.waitForLoadState("networkidle", { timeout: 30_000 }).catch(() => undefined);
  const settled = await page
    .waitForFunction(
      (markers) => !markers.some((marker) => document.body?.innerText.includes(marker)),
      loadingMarkers,
      { timeout: 30_000 },
    )
    .then(() => true)
    .catch(() => false);
  await page.waitForTimeout(300);
  return settled;
}

async function redactVisibleSecrets(page) {
  await page.evaluate((email) => {
    const emailPattern = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi;
    const phonePattern = /(?:\+?38)?0\d{9}/g;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      let text = node.nodeValue || "";
      if (email && text.includes(email)) text = text.replaceAll(email, "[EMAIL]");
      text = text.replace(emailPattern, "[EMAIL]").replace(phonePattern, "[PHONE]");
      node.nodeValue = text;
    }
  }, OWNER_EMAIL).catch(() => undefined);
}

async function main() {
  if (!BASE_URL || !OWNER_EMAIL || !OWNER_PASSWORD || !WORKSPACE_ID) {
    throw new Error("Required browser-matrix environment inputs are missing");
  }

  fs.mkdirSync(OUT_DIR, { recursive: true });
  const report = {
    sprint: "8E",
    phase: "browser-mobile-matrix",
    base_url: BASE_URL,
    decision: "FAIL",
    viewports: [],
    totals: { checks: 0, failed: 0, page_errors: 0, http_5xx: 0 },
    generated_at: new Date().toISOString(),
  };

  const browser = await chromium.launch({ headless: true });
  try {
    for (const viewport of viewports) {
      const result = {
        viewport,
        checks: [],
        routes: [],
        page_errors: [],
        console_errors: [],
        http_5xx: [],
      };
      const context = await browser.newContext({
        viewport: { width: viewport.width, height: viewport.height },
        locale: "uk-UA",
        colorScheme: "dark",
      });
      const page = await context.newPage();

      page.on("pageerror", (error) => result.page_errors.push(safeMessage(error.message)));
      page.on("console", (message) => {
        if (message.type() === "error") result.console_errors.push(safeMessage(message.text()));
      });
      page.on("response", (response) => {
        if (response.status() >= 500) {
          result.http_5xx.push({ status: response.status(), url: safeMessage(response.url()) });
        }
      });

      try {
        const loginResponse = await page.goto(`${BASE_URL}/login`, {
          waitUntil: "domcontentloaded",
          timeout: 90_000,
        });
        await page.waitForTimeout(500);
        const loginState = await pageState(page);
        const emailInput = page.locator('input[type="email"]');
        const passwordInput = page.locator('input[type="password"]');
        addCheck(result, "login page HTTP 200", loginResponse?.status() === 200, { status: loginResponse?.status() });
        addCheck(result, "login form visible", await emailInput.isVisible() && await passwordInput.isVisible());
        addCheck(result, "login page has no horizontal overflow", loginState.layout.documentWidth <= loginState.layout.viewportWidth + 4, loginState.layout);
        addCheck(result, "login page has no fatal marker", loginState.fatalMarkers.length === 0, { markers: loginState.fatalMarkers });
        await page.screenshot({ path: path.join(OUT_DIR, `${viewport.name}-login.png`), fullPage: true });

        await emailInput.fill(OWNER_EMAIL);
        await passwordInput.fill(OWNER_PASSWORD);
        await page.getByRole("button", { name: /Увійти|Sign in/i }).click();
        await page.waitForURL((url) => !url.pathname.endsWith("/login"), { timeout: 60_000 });
        await page.waitForLoadState("domcontentloaded");

        await page.evaluate((workspaceId) => {
          window.localStorage.setItem("sellora.current_workspace_id", workspaceId);
        }, WORKSPACE_ID);

        for (const route of protectedRoutes) {
          const routeResult = { route, checks: [] };
          const response = await page.goto(`${BASE_URL}${route}`, {
            waitUntil: "domcontentloaded",
            timeout: 90_000,
          });
          const settled = await waitForSettledRoute(page);
          const state = await pageState(page);
          const routeOk = response && response.status() >= 200 && response.status() < 400;
          const remainedAuthenticated = !new URL(state.currentUrl).pathname.endsWith("/login");
          const noOverflow = state.layout.documentWidth <= state.layout.viewportWidth + 4;
          const noFatal = state.fatalMarkers.length === 0;
          const noLoadingMarkers = state.loadingMarkers.length === 0;

          addCheck(routeResult, "HTTP success", Boolean(routeOk), { status: response?.status() });
          addCheck(routeResult, "authenticated route retained", remainedAuthenticated, { current_url: state.currentUrl });
          addCheck(routeResult, "main region present", state.layout.mainPresent, state.layout);
          addCheck(routeResult, "route loading state settled", settled && noLoadingMarkers, { markers: state.loadingMarkers });
          addCheck(routeResult, "no horizontal overflow", noOverflow, state.layout);
          addCheck(routeResult, "no fatal marker", noFatal, { markers: state.fatalMarkers });

          await redactVisibleSecrets(page);
          await page.screenshot({
            path: path.join(OUT_DIR, `${viewport.name}-${route.slice(1)}.png`),
            fullPage: true,
          });
          result.routes.push(routeResult);
        }

        addCheck(result, "no page runtime errors", result.page_errors.length === 0, result.page_errors);
        addCheck(result, "no console errors", result.console_errors.length === 0, result.console_errors);
        addCheck(result, "no HTTP 5xx responses", result.http_5xx.length === 0, result.http_5xx);
      } catch (error) {
        addCheck(result, "viewport execution completed", false, { error: safeMessage(error.message) });
      } finally {
        await context.close();
      }

      report.viewports.push(result);
    }
  } finally {
    await browser.close();
  }

  const allChecks = [];
  for (const viewport of report.viewports) {
    allChecks.push(...viewport.checks);
    for (const route of viewport.routes) allChecks.push(...route.checks);
    report.totals.page_errors += viewport.page_errors.length;
    report.totals.http_5xx += viewport.http_5xx.length;
  }
  report.totals.checks = allChecks.length;
  report.totals.failed = allChecks.filter((check) => check.status !== "PASS").length;
  report.decision = report.totals.failed === 0 ? "PASS" : "FAIL";
  report.generated_at = new Date().toISOString();

  fs.mkdirSync(path.dirname(REPORT_PATH), { recursive: true });
  fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify({
    decision: report.decision,
    checks: report.totals.checks,
    failed: report.totals.failed,
    page_errors: report.totals.page_errors,
    http_5xx: report.totals.http_5xx,
    artifact: REPORT_PATH,
  }));
  process.exit(report.decision === "PASS" ? 0 : 1);
}

main().catch((error) => {
  fs.mkdirSync(path.dirname(REPORT_PATH), { recursive: true });
  const failure = {
    sprint: "8E",
    phase: "browser-mobile-matrix",
    decision: "FAIL",
    safe_error: safeMessage(error.message),
    generated_at: new Date().toISOString(),
  };
  fs.writeFileSync(REPORT_PATH, JSON.stringify(failure, null, 2), "utf8");
  console.error(`SAFE_ERROR: ${failure.safe_error}`);
  process.exit(1);
});
