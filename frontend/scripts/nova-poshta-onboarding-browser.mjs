// Run against a local cookie-session frontend; all APIs are synthetic and all external requests blocked.
import { createRequire } from "node:module";
import { runNovaPoshtaOnboardingScenario, assertNovaPoshtaControlBounds } from "./nova-poshta-onboarding-browser-fixture.mjs";
const require = createRequire(process.env.PLAYWRIGHT_RUNTIME_PACKAGE || import.meta.url);
const { chromium, expect } = require("@playwright/test");
const base = process.env.NP_TEST_BASE_URL || "http://127.0.0.1:3141";
if (!["127.0.0.1", "localhost"].includes(new URL(base).hostname)) throw new Error("Synthetic runner requires localhost");
const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || "/usr/bin/chromium" });
try {
  for (const width of [1366, 390]) {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const workspaceId = "11111111-1111-4111-8111-111111111111";
    const user = { id: "22222222-2222-4222-8222-222222222222", email: "synthetic@example.invalid", first_name: "Тест", last_name: "Sellora", is_active: true, memberships: [{ workspace_id: workspaceId, workspace_name: "Синтетичний магазин", role: "OWNER", currency_code: "UAH" }] };
    await context.addCookies([{ name: "sellora_session_refresh", value: "synthetic-browser-session", domain: new URL(base).hostname, path: "/api/v1/auth/session", httpOnly: true, sameSite: "Lax" }]);
    await context.addInitScript(id => localStorage.setItem("sellora.current_workspace_id", id), workspaceId);
    await context.route("**/*", async route => {
      const request = route.request(), url = new URL(request.url());
      if (url.origin !== new URL(base).origin) return route.abort();
      if (!url.pathname.startsWith("/api/")) return route.continue();
      const json = url.pathname.endsWith("/auth/session/refresh") ? { access_token: "synthetic-browser-fixture", token_type: "bearer" } : url.pathname.endsWith("/auth/me") ? user : url.pathname.endsWith("/direct/live-summary") ? { server_time: "2026-10-20T10:00:00Z", unread_total: 0, order_intent_count: 0, events: [] } : url.pathname.includes("instagram") ? { status: "DISCONNECTED", token_present: false, webhook_active: false, granted_permissions: [], confirmed_webhook_fields: [] } : url.pathname.includes("meta-ads") ? { status: "DISCONNECTED", connected: false, blockers: [] } : [];
      if (request.method() !== "GET" && !url.pathname.endsWith("/auth/session/refresh")) throw new Error(`Unexpected write ${url.pathname}`);
      return route.fulfill({ json });
    });
    const page = await context.newPage();
    page.setDefaultTimeout(10000);
    const errors = [];
    page.on("pageerror", error => errors.push(error.stack));
    let state;
    try { state = await runNovaPoshtaOnboardingScenario({ page, expect, base, width }); } catch (error) { console.log("DIAGNOSTIC", page.url(), errors, (await page.locator("body").innerText()).slice(0, 2000)); throw error; }
    await assertNovaPoshtaControlBounds(page, expect);
    await page.locator("[data-nova-poshta-settings]").screenshot({ path: `/tmp/sellora-np-onboarding-populated-${width}.png` });
    await page.getByLabel("Контактна особа", { exact: true }).selectOption("");
    await page.getByRole("button", { name: "Зберегти API-ключ", exact: true }).click();
    await expect.poll(() => state.settings.sender_contact_ref).toBe(null);
    expect(state.settings.connection_verified).toBe(false);
    expect(state.settings.workspace_permission).toBe(false);
    await page.getByLabel("Відправник", { exact: true }).selectOption("");
    await page.getByRole("button", { name: "Зберегти API-ключ", exact: true }).click();
    await expect.poll(() => state.settings.sender_counterparty_ref).toBe(null);
    expect(state.payloads.at(-1)).toMatchObject({ api_key: null, sender_counterparty_ref: null, sender_contact_ref: null, sender_city_ref: null, sender_warehouse_ref: null });
    state.failLookup = true;
    await page.getByLabel("Пошук відправника за назвою", { exact: true }).fill("помилка");
    await expect(page.getByRole("alert").filter({ hasText: "Не вдалося завантажити" })).toBeVisible();
    await assertNovaPoshtaControlBounds(page, expect);
    expect(errors).toEqual([]);
    await page.screenshot({ path: `/tmp/sellora-np-onboarding-${width}.png`, fullPage: true });
    console.log(`PASS ${width}: save key, named sender/contact/city/warehouse, dependent reset, blank key payload, verify, writes off, failed lookup, no browser key persistence, no overflow/occlusion/runtime errors`);
    await context.close();
  }
} finally { await browser.close(); }
