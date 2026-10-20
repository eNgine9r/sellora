// Run against a local cookie-session frontend; all APIs are synthetic and all external requests blocked.
import { writeFile } from "node:fs/promises";
import path from "node:path";
import { integrationRuntime } from "./integrations-browser-runtime.mjs";
import { runNovaPoshtaOnboardingScenario, assertNovaPoshtaControlBounds } from "./nova-poshta-onboarding-browser-fixture.mjs";
const runtime = await integrationRuntime("nova-poshta");
const { browser, expect, base, output } = runtime;
const checks = [], failures = [];
try {
  for (const width of [1366, 390]) {
    const context = await browser.newContext({ serviceWorkers: "block" });
    const workspaceId = "11111111-1111-4111-8111-111111111111";
    const user = { id: "22222222-2222-4222-8222-222222222222", email: "synthetic@example.invalid", first_name: "Тест", last_name: "Sellora", is_active: true, memberships: [{ workspace_id: workspaceId, workspace_name: "Синтетичний магазин", role: "OWNER", currency_code: "UAH" }, { workspace_id: "44444444-4444-4444-8444-444444444444", workspace_name: "Другий синтетичний магазин", role: "OWNER", currency_code: "UAH" }] };
    await context.addCookies([{ name: "sellora_session_refresh", value: "synthetic-browser-session", domain: new URL(base).hostname, path: "/api/v1/auth/session", httpOnly: true, secure: new URL(base).protocol === "https:", sameSite: "Lax" }]);
    await context.addInitScript(id => localStorage.setItem("sellora.current_workspace_id", id), workspaceId);
    const refresh = { hold: false, release: null };
    const unexpected = [];
    await context.route("**/*", async route => {
      const request = route.request(), url = new URL(request.url());
      if (url.origin !== new URL(base).origin) { unexpected.push("external request"); return route.abort(); }
      if (!url.pathname.startsWith("/api/")) return route.continue();
      if (!["/api/v1/auth/session/refresh", "/api/v1/auth/me", "/api/v1/direct/live-summary", "/api/v1/integrations/instagram/status", "/api/v1/integrations/meta-ads/status"].includes(url.pathname)) {
        unexpected.push(request.method() + " " + url.pathname); return route.fulfill({ status: 500, json: {} });
      }
      if (url.pathname.endsWith("/auth/session/refresh") && !((await request.allHeaders()).cookie ?? "").includes("sellora_session_refresh=synthetic-browser-session")) return route.fulfill({ status: 401, json: {} });
      if (url.pathname.endsWith("/auth/session/refresh") && refresh.hold) await new Promise(resolve => { refresh.release = resolve; });
      const json = url.pathname.endsWith("/auth/session/refresh") ? { access_token: "synthetic-browser-fixture", token_type: "bearer" } : url.pathname.endsWith("/auth/me") ? user : url.pathname.endsWith("/direct/live-summary") ? { server_time: "2026-10-20T10:00:00Z", unread_total: 0, order_intent_count: 0, events: [] } : url.pathname.includes("instagram") ? { status: "DISCONNECTED", token_present: false, webhook_active: false, granted_permissions: [], confirmed_webhook_fields: [] } : url.pathname.includes("meta-ads") ? { workspace_id: workspaceId, connection_status: "NOT_CONNECTED", connected: false, configured: false, can_connect: false, can_sync: false, sync_enabled: false, blockers: ["feature_disabled"] } : [];
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
    await page.locator("[data-nova-poshta-settings]").screenshot({ path: path.join(output, `populated-${width}.png`) });
    const switchWorkspace = async second => {
      if (await page.locator(".account-profile-trigger").isVisible()) await page.locator(".account-profile-trigger").click();
  else await page.locator('.mobile-bottom-nav button[aria-label="Профіль"]').click();
      await page.getByRole("button", { name: second ? /Другий синтетичний магазин/ : /^Синтетичний магазин/ }).click();
    };
    state.holdTest = true;
    await page.getByRole("button", { name: "Перевірити підключення", exact: true }).click();
    await expect.poll(() => typeof state.releaseTest).toBe("function");
    await switchWorkspace(true);
    state.releaseTest(); state.holdTest = false;
    await expect(page.getByText("Перевірку пройдено. Створення накладних залишається вимкненим до вашого окремого дозволу.")).toHaveCount(0);
    await expect(page.getByText("API-ключ і дані відправника Нової Пошти успішно перевірено.")).toHaveCount(0);
    await switchWorkspace(false);
    state.retry401 = true; refresh.hold = true;
    const beforeRetry = state.testCalls.length;
    await page.getByRole("button", { name: "Перевірити підключення", exact: true }).click();
    await expect.poll(() => typeof refresh.release).toBe("function");
    await switchWorkspace(true);
    refresh.hold = false; refresh.release();
    await expect(page.locator("[data-nova-poshta-settings]")).toBeVisible();
    expect(state.testCalls.length).toBe(beforeRetry + 1);
    expect(state.testCalls.every(id => id === workspaceId)).toBe(true);
    await expect(page.getByText("Перевірку пройдено. Створення накладних залишається вимкненим до вашого окремого дозволу.")).toHaveCount(0);
    await expect(page.getByText("API-ключ і дані відправника Нової Пошти успішно перевірено.")).toHaveCount(0);
    await switchWorkspace(false);
    await page.getByLabel("Контактна особа", { exact: true }).selectOption("");
    const settingsRefetch = page.waitForResponse(response => response.url().endsWith("/integrations/nova-poshta/settings") && response.request().method() === "GET");
    await page.getByRole("button", { name: "Зберегти API-ключ", exact: true }).click();
    await settingsRefetch;
    await expect.poll(() => state.settings.sender_contact_ref).toBe(null);
    expect(state.settings.connection_verified).toBe(false);
    expect(state.settings.workspace_permission).toBe(false);
    await page.getByLabel("Відправник", { exact: true }).selectOption("");
    const secondRefetch = page.waitForResponse(response => response.url().endsWith("/integrations/nova-poshta/settings") && response.request().method() === "GET");
    await page.getByRole("button", { name: "Зберегти API-ключ", exact: true }).click();
    await secondRefetch;
    await expect.poll(() => state.settings.sender_counterparty_ref).toBe(null);
    expect(state.payloads.at(-1)).toMatchObject({ api_key: null, sender_counterparty_ref: null, sender_contact_ref: null, sender_city_ref: null, sender_warehouse_ref: null });
    state.failLookup = true;
    await page.getByLabel("Пошук відправника за назвою", { exact: true }).fill("помилка");
    await expect(page.getByRole("alert").filter({ hasText: "Не вдалося завантажити" })).toBeVisible();
    await assertNovaPoshtaControlBounds(page, expect);
    expect(errors).toEqual([]);
    expect(unexpected).toEqual([]);
    await page.screenshot({ path: path.join(output, `onboarding-${width}.png`), fullPage: true });
    checks.push(`${width}: delayed verification success and401 stay scoped across workspace switch; named sender/contact/address, dependency clearing, verify, write gates, key privacy, bounds`);
    console.log(`PASS ${width}: save key, named sender/contact/city/warehouse, dependent reset, blank key payload, verify, writes off, failed lookup, no browser key persistence, no overflow/occlusion/runtime errors`);
    await context.close();
  }
} catch (error) { failures.push(error.stack); throw error; }
finally { await writeFile(path.join(output, "result.json"), JSON.stringify({ syntheticOnly: true, checks, failures }, null, 2)); await runtime.close(); }
