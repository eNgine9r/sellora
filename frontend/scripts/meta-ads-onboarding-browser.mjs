// Synthetic only: every API is intercepted and every external request is blocked.
import { writeFile } from "node:fs/promises";
import path from "node:path";
import { integrationRuntime } from "./integrations-browser-runtime.mjs";
import { assertNovaPoshtaControlBounds } from "./nova-poshta-onboarding-browser-fixture.mjs";
const runtime = await integrationRuntime(process.env.INTEGRATIONS_TEST_DEV === "1" ? "meta-ads-strictmode" : "meta-ads");
const { browser, expect, base, output } = runtime;
const w1 = "11111111-1111-4111-8111-111111111111", w2 = "44444444-4444-4444-8444-444444444444";
const actor = "22222222-2222-4222-8222-222222222222";
const checks = [], failures = [];
const statuses = () => ({ workspace_id: w1, connection_status: "NOT_CONNECTED", connected: false, configured: true, can_connect: true, can_sync: false, sync_enabled: true, account_selection_required: false, blockers: [], account_name: null, currency: null, timezone: null, last_synced_at: null, last_error_code: null });
async function fixture(width, role = "OWNER") {
  const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: "block" });
  await context.addCookies([{ name: "sellora_session_refresh", value: "synthetic-browser-session", domain: new URL(base).hostname, secure: new URL(base).protocol === "https:", path: "/api/v1/auth/session", httpOnly: true, sameSite: "Lax" }]);
  await context.addInitScript(id => { if (!localStorage.getItem("sellora.current_workspace_id")) localStorage.setItem("sellora.current_workspace_id", id); }, w1);
  const user = { id: actor, email: "synthetic@example.invalid", first_name: "Тест", last_name: "Sellora", is_active: true, memberships: [{ workspace_id: w1, workspace_name: "Синтетичний магазин", role, currency_code: "UAH" }, { workspace_id: w2, workspace_name: "Другий синтетичний магазин", role, currency_code: "UAH" }] };
  const state = { status: statuses(), calls: [], external: [], unexpected: [], errors: [], syncError: null, hold: null, release: null, failStatus: false, accounts: true, callbackError: false, holdRefresh: false, releaseRefresh: null, retry401: false, callbackCount: 0, metricConflict: false, metricPayload: null };
  const campaign = { id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", workspace_id: w1, name: "Meta synthetic", platform: "INSTAGRAM", status: "ACTIVE", objective: "MESSAGES", budget_type: "DAILY" };
  const metric = { id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", campaign_id: campaign.id, workspace_id: w1, metric_date: "2026-10-20", source_type: "meta_live", provider_controlled_fields: ["metric_date", "spend", "impressions", "clicks", "messages"], spend: "100", impressions: 1000, reach: 0, clicks: 20, messages: 5, leads: 0, orders: 0, revenue: "0", net_profit: "0" };
  await context.route("**/*", async route => {
    const r = route.request(), url = new URL(r.url()), method = r.method(), endpoint = url.pathname, workspace = r.headers()["x-workspace-id"];
    const ok = (json, status = 200) => route.fulfill({ json, status });
    if (url.origin !== new URL(base).origin) { state.external.push(url.origin); return route.fulfill({ contentType: "text/html", body: "<!doctype html><title>Synthetic provider navigation intercepted</title>" }); }
    if (!endpoint.startsWith("/api/")) return route.continue();
    state.calls.push({ method, endpoint, workspace });
    if (endpoint === "/api/v1/auth/session/refresh") {
      if (state.holdRefresh) await new Promise(resolve => { state.releaseRefresh = resolve; });
      const hasCookie = ((await r.allHeaders()).cookie ?? "").includes("sellora_session_refresh=synthetic-browser-session");
      return ok(hasCookie ? { access_token: "synthetic-access", token_type: "bearer" } : {}, hasCookie ? 200 : 401);
    }
    if (endpoint === "/api/v1/auth/me") return ok(user);
    if (endpoint === "/api/v1/auth/session/logout") return ok({});
    if (endpoint === "/api/v1/direct/live-summary") return ok({ server_time: "2026-10-20T10:00:00Z", unread_total: 0, order_intent_count: 0, events: [] });
    if (endpoint === "/api/v1/integrations/instagram/status") return ok({ status: "DISCONNECTED", token_present: false, webhook_active: false, granted_permissions: [], confirmed_webhook_fields: [] });
    if (endpoint === "/api/v1/integrations/nova-poshta/settings") return ok({ status: "DISCONNECTED", masked_api_key: null, workspace_permission: false, environment_capability: false });
    if (endpoint.startsWith("/api/v1/integrations/meta-ads/")) {
      if (![w1, w2].includes(workspace)) throw new Error("Missing originating workspace");
      const part = endpoint.split("/meta-ads/")[1];
      if (method === "GET" && part === "status") return state.failStatus ? ok({}, 503) : ok(workspace === w1 ? state.status : { ...statuses(), workspace_id: w2 });
      if (method === "GET" && part === "accounts") return ok({ accounts: state.accounts ? [{ external_account_id: "act_123", name: "Тестовий кабінет", currency: "UAH", timezone: "Europe/Kyiv", selectable: true, reason: null }, { external_account_id: "act_456", name: "Інша валюта", currency: "USD", timezone: "America/New_York", selectable: false, reason: "currency_mismatch" }] : [], selected_account_id: state.status.account_name ? "act_123" : null, workspace_currency: "UAH", workspace_timezone: "Europe/Kyiv" });
      if (role !== "OWNER") return ok({ detail: { code: "ownerOnly" } }, 403);
      if (part === "oauth/start") return ok({ ...state.status, authorization_url: "https://www.facebook.com/v26.0/dialog/oauth?state=synthetic-state", state_expires_at: "2099-10-20T10:00:00Z" });
      if (part === "oauth/callback") {
        state.callbackCount++;
        if (state.callbackError) return ok({ detail: { code: "invalid_state" } }, 400);
        expect(r.headers()["referer"]).toBeUndefined();
        expect(r.postDataJSON()).toEqual({ code: "synthetic-code", state: "synthetic-state" });
        state.status = { ...state.status, connected: true, connection_status: "CONNECTED", account_selection_required: true };
        return ok({ ...state.status, token_stored: true });
      }
      if (part === "account") {
        expect(r.postDataJSON()).toEqual({ external_account_id: "act_123" });
        state.status = { ...state.status, account_name: "Тестовий кабінет", currency: "UAH", timezone: "Europe/Kyiv", account_selection_required: false, can_sync: true };
        return ok(state.status);
      }
      if (part === "sync") {
        if (state.hold === "sync") await new Promise(resolve => { state.release = resolve; });
        if (state.retry401) { state.retry401 = false; return ok({}, 401); }
        if (state.syncError) return ok({ detail: { code: state.syncError } }, 409);
        state.status.last_synced_at = "2026-10-20T12:00:00Z";
        return ok({ status: "SUCCEEDED", metrics_created: 1, metrics_updated: 0, last_synced_at: state.status.last_synced_at, reach_measure: "not_imported" });
      }
      if (part === "disconnect") { state.status = statuses(); return ok({ ...state.status, disconnected: true }); }
    }
    if (method === "GET" && endpoint === "/api/v1/advertising/campaigns") return ok([campaign]);
    if (method === "GET" && endpoint === "/api/v1/advertising/metrics") return ok([metric]);
    if (method === "PUT" && endpoint.endsWith("/metrics/" + metric.id)) { state.metricPayload = r.postDataJSON(); if (state.metricConflict) return ok({ detail: { code: "provider_metric_read_only" } }, 409); Object.assign(metric, state.metricPayload); return ok(metric); }
    if (method === "GET" && ["/api/v1/advertising/campaign-performance", "/api/v1/advertising/trend", "/api/v1/orders", "/api/v1/products", "/api/v1/customers"].includes(endpoint)) return ok([]);
    if (method === "GET" && endpoint === "/api/v1/advertising/summary") return ok({ total_spend: "100", total_impressions: 1000, total_reach: 0, total_clicks: 20, total_messages: 5, total_leads: 0, total_orders: 0, total_revenue: "0", total_net_profit: "0" });
    if (method === "GET" && endpoint === "/api/v1/advertising/crm-attribution") return ok({ totals: {}, unattributed: {}, campaigns: [], attribution_coverage_percent: null, start_date: "2026-10-20", end_date: "2026-10-20" });
    state.unexpected.push(method + " " + endpoint); return ok({}, 500);
  });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  page.on("pageerror", error => state.errors.push(error.message));
  const card = () => page.locator("[data-meta-ads-settings]");
  const clean = async () => { expect(state.errors).toEqual([]); expect(state.unexpected).toEqual([]); };
  return { context, page, state, card, clean };
}
async function switchWorkspace(page, second) {
  if (await page.locator(".account-profile-trigger").isVisible()) await page.locator(".account-profile-trigger").click();
  else await page.locator('.mobile-bottom-nav button[aria-label="Профіль"]').click();
  await page.getByRole("button", { name: second ? /Другий синтетичний магазин/ : /^Синтетичний магазин/ }).click();
}
async function connect(f) {
  await f.page.goto(base + "/settings/integrations");
  // Record outbound navigation while blocking it before any provider traffic.
  await f.card().getByRole("button", { name: "Підключити Meta Ads", exact: true }).click();
  await expect.poll(() => f.state.external.length).toBe(1);
  await f.page.waitForURL("https://www.facebook.com/**");
  await f.page.waitForLoadState("load");
  f.state.holdRefresh = true; f.state.releaseRefresh = null;
  const callbackResponse = await f.page.goto(base + "/settings/integrations/meta-ads/callback?code=synthetic-code&state=synthetic-state");
  expect(callbackResponse.headers()["referrer-policy"]).toBe("no-referrer");
  expect(callbackResponse.headers()["cache-control"]).toContain("no-store");
  await expect.poll(() => typeof f.state.releaseRefresh).toBe("function");
  expect(new URL(f.page.url()).search).toBe("");
  f.state.holdRefresh = false; f.state.releaseRefresh();
  await expect(f.page.getByText("Meta Ads підключено. Тепер оберіть рекламний кабінет.")).toBeVisible();
  expect(new URL(f.page.url()).search).toBe("");
  expect(f.state.callbackCount).toBe(1);
  expect(await f.page.evaluate(() => "__selloraMetaAdsCallback" in window)).toBe(false);
  expect(await f.page.evaluate(() => [localStorage, sessionStorage].some(storage => Object.values(storage).some(value => /synthetic-code|synthetic-access/.test(value))))).toBe(false);
  await f.page.reload();
  await expect(f.page.getByText("Meta Ads підключено. Тепер оберіть рекламний кабінет.")).toBeVisible();
  expect(f.state.callbackCount).toBe(1);
  await f.page.getByRole("link", { name: "До інтеграцій" }).click();
  await expect(f.card().getByRole("combobox", { name: "Рекламний кабінет", exact: true })).toHaveValue("");
  await expect(f.card().getByRole("button", { name: "Синхронізувати період" })).toBeDisabled();
}
try {
  const callbackOnly = process.env.META_ADS_TEST_SUITE === "callback";
  const denialOnly = process.env.META_ADS_TEST_SUITE === "denial";
  for (const width of denialOnly ? [] : callbackOnly ? [1366] : [1366, 390]) {
    const f = await fixture(width);
    try {
      await connect(f);
      if (callbackOnly) { await f.clean(); checks.push("Next development StrictMode: callback scrub, one POST, reload recovery"); continue; }
      const picker = f.card().getByRole("combobox", { name: "Рекламний кабінет", exact: true });
      await expect(picker.locator('option[value="act_456"]')).toHaveAttribute("disabled", "");
      await picker.selectOption("act_123");
      await f.card().getByRole("button", { name: "Підтвердити кабінет" }).click();
      await expect(f.card().getByRole("button", { name: "Синхронізувати період" })).toBeEnabled();
      await f.card().getByLabel("Початок синхронізації").fill("2026-01-01");
      await f.card().getByLabel("Кінець синхронізації").fill("2026-10-20");
      await expect(f.card().getByRole("button", { name: "Синхронізувати період" })).toBeDisabled();
      await f.card().getByLabel("Початок синхронізації").fill("2026-10-20");
      for (let i = 0; i < 2; i++) {
        await f.card().getByRole("button", { name: "Синхронізувати період" }).click();
        await expect(f.card().getByText(/Період синхронізовано/)).toBeVisible();
      }
      expect(f.state.calls.filter(c => c.endpoint.endsWith("/sync")).length).toBe(2);
      for (const code of ["manual_spend_conflict", "currency_mismatch", "RATE_LIMITED", "TOKEN_EXPIRED", "NETWORK_ERROR"]) {
        f.state.syncError = code;
        await f.card().getByRole("button", { name: "Синхронізувати період" }).click();
        const copy = { manual_spend_conflict: "Синхронізацію скасовано", currency_mismatch: "Валюта кабінету", RATE_LIMITED: "Meta тимчасово", TOKEN_EXPIRED: "Термін доступу", NETWORK_ERROR: "Meta не відповідає" };
        await expect(f.card().getByRole("status")).toContainText(copy[code]);
      }
      f.state.syncError = null;
      await assertNovaPoshtaControlBounds(f.page, expect, "[data-meta-ads-settings]");
      expect(await f.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await f.card().screenshot({ path: path.join(output, "connected-" + width + ".png") });
      // A late success remains with workspace A.
      f.state.hold = "sync";
      await f.card().getByRole("button", { name: "Синхронізувати період" }).click();
      await expect.poll(() => typeof f.state.release).toBe("function");
      await switchWorkspace(f.page, true);
      f.state.release();
      await expect(f.card().getByText(/Період синхронізовано/)).toHaveCount(0);
      await expect(f.card().getByText("Не підключено", { exact: true })).toBeVisible();
      await switchWorkspace(f.page, false);
      // A401 followed by a delayed refresh must not retry the old sync in B.
      f.state.hold = null; f.state.retry401 = true; f.state.holdRefresh = true;
      const before = f.state.calls.filter(c => c.endpoint.endsWith("/sync")).length;
      await f.card().getByRole("button", { name: "Синхронізувати період" }).click();
      await expect.poll(() => typeof f.state.releaseRefresh).toBe("function");
      await switchWorkspace(f.page, true);
      f.state.holdRefresh = false; f.state.releaseRefresh();
      await expect(f.card().getByText("Не підключено", { exact: true })).toBeVisible();
      expect(f.state.calls.filter(c => c.endpoint.endsWith("/sync")).length).toBe(before + 1);
      expect(f.state.calls.filter(c => c.method !== "GET" && c.workspace === w2)).toEqual([]);
      await switchWorkspace(f.page, false);
      await f.card().getByRole("button", { name: "Відключити Meta Ads", exact: true }).click();
      await expect(f.card().getByRole("button", { name: "Підтвердити відключення" })).toBeVisible();
      await f.card().getByRole("button", { name: "Підтвердити відключення" }).click();
      await expect(f.card().getByText("Не підключено", { exact: true })).toBeVisible();
      await f.clean();
      checks.push(width + ": connect, sanitized callback, reload/no replay, explicit picker, currency, bounded range, repeat sync, errors, workspace late success and401, confirmed disconnect, control bounds");
    } catch (error) { await f.page.screenshot({ path: path.join(output, "failure-" + width + ".png"), fullPage: true }); throw error; }
    finally { await f.context.close(); }
  }
  if (!callbackOnly) {
  for (const mode of denialOnly ? ["denial"] : ["blocked", "empty", "statusError", "denial", "expired", "actorMismatch", "workspaceMismatch", "callbackError", "logout", "reconnect", "analyst", "manager"]) {
    const f = await fixture(390, mode === "analyst" ? "ANALYST" : mode === "manager" ? "MANAGER" : "OWNER");
    try {
      if (mode === "reconnect") f.state.status.connection_status = "TOKEN_EXPIRED";
      if (mode === "blocked") { f.state.status.can_connect = false; f.state.status.blockers = ["missing_required_configuration"]; }
      if (mode === "empty") { f.state.status.connected = true; f.state.status.connection_status = "CONNECTED"; f.state.accounts = false; }
      if (mode === "statusError") f.state.failStatus = true;
      if (["denial", "expired", "actorMismatch", "workspaceMismatch", "callbackError"].includes(mode)) {
        await f.page.goto(base + "/settings/integrations");
        await expect(f.card().getByRole("button", { name: "Підключити Meta Ads", exact: true })).toBeVisible();
        await f.page.evaluate(({ actor, w1, mode }) => sessionStorage.setItem("sellora.meta-ads.intent", JSON.stringify({ actor: mode === "actorMismatch" ? "other" : actor, workspace: mode === "workspaceMismatch" ? "other" : w1, state: "synthetic-state", phase: "pending", expires: mode === "expired" ? "2000-01-01" : "2099-01-01" })), { actor, w1, mode });
        f.state.callbackError = mode === "callbackError";
        await f.page.goto(base + "/settings/integrations/meta-ads/callback?" + (mode === "denial" ? "error=access_denied" : "state=synthetic-state&code=synthetic-code"));
        await expect(f.page.getByText(mode === "denial" ? /Ви скасували підключення/ : /Підключення не підтверджено/)).toBeVisible();
        expect(new URL(f.page.url()).search).toBe("");
        expect(await f.page.evaluate(() => sessionStorage.getItem("sellora.meta-ads.intent"))).toBe(null);
        expect(f.state.callbackCount).toBe(mode === "callbackError" ? 1 : 0);
      } else {
        await f.page.goto(base + "/settings/integrations");
        if (mode === "logout") {
          await f.page.evaluate(({ actor, w1 }) => sessionStorage.setItem("sellora.meta-ads.intent", JSON.stringify({ actor, workspace: w1, state: "synthetic-state", phase: "pending", expires: "2099-01-01" })), { actor, w1 });
          await f.page.locator('.mobile-bottom-nav button[aria-label="Профіль"]').click();
          await f.page.getByRole("button", { name: "Вийти", exact: true }).click();
          await expect(f.page).toHaveURL(/\/login$/);
          expect(await f.page.evaluate(() => sessionStorage.getItem("sellora.meta-ads.intent"))).toBe(null);
        }
        if (mode === "reconnect") {
          await expect(f.card().getByRole("button", { name: "Підключити повторно" })).toBeEnabled();
          await f.card().getByRole("button", { name: "Відключити Meta Ads", exact: true }).click();
          await f.card().getByRole("button", { name: "Підтвердити відключення" }).click();
          await expect(f.card().getByText("Не підключено", { exact: true })).toBeVisible();
        }
        if (mode === "blocked") await expect(f.card().getByRole("button", { name: "Підключити Meta Ads" })).toBeDisabled();
        if (mode === "empty") await expect(f.card().getByText(/Немає доступних рекламних кабінетів/)).toBeVisible();
        if (mode === "statusError") await expect(f.card().getByRole("alert")).toContainText("Не вдалося завантажити");
        if (mode === "analyst" || mode === "manager") { await expect(f.card().getByText(/Підключенням і синхронізацією керує власник/)).toBeVisible(); expect(f.state.calls.filter(c => c.method !== "GET" && !c.endpoint.endsWith("/refresh"))).toEqual([]); }
      }
      await f.clean(); checks.push(mode);
    } finally { await f.context.close(); }
  }
  if (!denialOnly) {
  const f = await fixture(1366);
  try {
    await f.page.goto(base + "/advertising");
    await f.page.getByRole("button", { name: "Редагувати метрику 2026-10-20", exact: true }).click();
    const dialog = f.page.getByRole("dialog");
    for (const label of ["Дата метрики", "Витрати", "Покази", "Кліки", "Повідомлення"]) await expect(dialog.getByLabel(label, { exact: true })).toBeDisabled();
    await expect(dialog.getByLabel("Локальне охоплення (не Meta)")).toBeEnabled();
    await dialog.getByLabel("Ліди", { exact: true }).fill("3");
    await dialog.getByRole("button", { name: "Зберегти зміни" }).click();
    await expect.poll(() => f.state.metricPayload?.leads).toBe(3);
    f.state.metricConflict = true;
    await f.page.getByRole("button", { name: "Редагувати метрику 2026-10-20", exact: true }).click();
    await dialog.getByLabel("Ліди", { exact: true }).fill("4");
    await dialog.getByRole("button", { name: "Зберегти зміни" }).click();
    await expect(dialog.getByText(/Поля доставки та дату контролює Meta Ads/)).toBeVisible();
    await f.clean(); checks.push("metric editor: protected fields disabled, local CRM saved, stale409 explained");
    await dialog.screenshot({ path: path.join(output, "metric-editor.png") });
  } finally { await f.context.close(); }
  }
  }
  console.log("Meta Ads synthetic gate passed: " + checks.length + " scenarios");
} catch (error) { failures.push(error.stack); throw error; }
finally { await writeFile(path.join(output, "result.json"), JSON.stringify({ syntheticOnly: true, checks, failures }, null, 2)); await runtime.close(); }
