// Synthetic-only browser gate. Every API call, including mount-time writes, is intercepted.
import { createRequire } from "node:module";
import { createServer } from "node:net";
import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createFulfillmentFixture } from "./fulfillment-browser-fixture.mjs";
import { runFulfillmentScenarios } from "./fulfillment-browser-scenarios.mjs";
const require = createRequire(process.env.PLAYWRIGHT_RUNTIME_PACKAGE || import.meta.url);
const { chromium, expect } = require("@playwright/test");
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const output = path.join(root, "artifacts/direct-modernization");
let base = process.env.DIRECT_TEST_BASE_URL;
let origin = base ? new URL(base).origin : null;
const workspaceId = "11111111-1111-4111-8111-111111111111";
const secondWorkspaceId = "44444444-4444-4444-8444-444444444444";
const d = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
const a = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const b = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const c = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const conversations = [
  { id: a, participant_display_name: "Олена Тестова", participant_username: "olena_fixture", channel: "INSTAGRAM", unread_count: 2 },
  { id: b, participant_display_name: "Марія Синтетична", participant_username: "maria_fixture", channel: "SYNTHETIC", unread_count: 0 },
  { id: c, participant_display_name: "Софія Приклад", participant_username: "sofia_fixture", channel: "INSTAGRAM", unread_count: 0 },
].map((item) => ({ ...item, status: "OPEN", priority: "NORMAL", ai_processing_status: "IDLE", participant_profile_status: "READY", messaging_window_expires_at: "2099-10-19T20:00:00Z", last_message_at: "2026-10-19T10:00:00Z" }));
const failures = [];
const checks = [];
const fixturePages = [];
let server;
let browser;
await mkdir(output, { recursive: true });

async function fixture(viewport, { role = "OWNER", theme = "light", delayedSuggestions = false, multiWorkspace = false, fulfillment = false } = {}) {
  const context = await browser.newContext({ viewport, colorScheme: theme, serviceWorkers: "block" });
  const user = { id: "22222222-2222-4222-8222-222222222222", email: "synthetic@example.invalid", first_name: "Тест", last_name: "Sellora", is_active: true, last_login_at: null, memberships: [{ workspace_id: workspaceId, workspace_name: "Синтетичний магазин", workspace_slug: "synthetic", role, currency_code: "UAH" }] };
  if (multiWorkspace) user.memberships.push({ ...user.memberships[0], workspace_id: secondWorkspaceId, workspace_name: "Другий синтетичний магазин", workspace_slug: "synthetic-second" });
  await context.addInitScript(({ user, workspaceId, theme }) => {
    localStorage.setItem("sellora.access_token", "synthetic-browser-fixture");
    localStorage.setItem("sellora.current_user", JSON.stringify(user));
    localStorage.setItem("sellora.current_workspace_id", workspaceId);
    localStorage.setItem("sellora.theme-mode", theme);
  }, { user, workspaceId, theme });
  const api = [];
  const unexpected = [];
  const errors = [];
  const state = { sendStatus: "COMPLETED", holdSend: false, releaseSend: null, prepareError: false, releaseSuggestions: null, operationStatus: null, holdStatus: false, releaseStatus: null, abortSend: false, statusRequests: 0, extraTimeline: [], appendSentTimeline: false };
  const fulfillmentFixture = fulfillment ? createFulfillmentFixture({ workspaceId, conversationId: a }) : null;
  state.fulfillment = fulfillmentFixture;
  const operations = new Map();
  let operationSequence = 0;
  const suggestionsReady = delayedSuggestions ? new Promise((resolve) => { state.releaseSuggestions = resolve; }) : Promise.resolve();
  await context.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.origin !== origin) {
      unexpected.push(`External request: ${url.origin}${url.pathname}`);
      await route.abort(); return;
    }
    if (!url.pathname.startsWith("/api/")) { await route.continue(); return; }
    const key = `${request.method()} ${url.pathname}`;
    const requestWorkspace = request.headers()["x-workspace-id"];
    const scopedConversations = requestWorkspace === secondWorkspaceId ? [{ ...conversations[0], id: d, participant_display_name: "Ірина Другого Магазину", unread_count: 0 }] : conversations;
    api.push(key);
    const respond = (data, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(data) });
    if (key === "GET /api/v1/auth/me") return respond(user);
    if (key === "GET /api/v1/direct/live-summary" && requestWorkspace === secondWorkspaceId) return respond({ server_time: "2026-10-19T10:00:00Z", unread_total: 0, order_intent_count: 0, events: [] });
    if (key === "GET /api/v1/direct/live-summary") return respond({ server_time: "2026-10-19T10:00:00Z", unread_total: 2, order_intent_count: 1, events: [{ message_id: "synthetic-event", conversation_id: a, participant_display_name: "Олена Тестова", text_preview: "Хочу замовити", order_intent: true, order_intent_confidence: 0.9, unread_count: 2, received_at: "2026-10-19T10:00:00Z" }] });
    if (key === "GET /api/v1/direct/conversations") return respond(fulfillmentFixture ? fulfillmentFixture.conversations(scopedConversations) : scopedConversations);
    if (key === "GET /api/v1/direct/history-sync") return respond(null);
    if (key === "GET /api/v1/integrations/instagram/status") return respond({ status: "CONNECTED", token_present: true, webhook_active: true });
    const operationMatch = url.pathname.match(/^\/api\/v1\/direct\/message-operations\/([^/]+)$/);
    if (request.method() === "GET" && operationMatch) {
      const operation = operations.get(operationMatch[1]);
      if (!operation || operation.workspaceId !== requestWorkspace) { unexpected.push(`Wrong operation workspace: ${key}`); return respond({ detail: "Unexpected operation" }, 404); }
      state.statusRequests++;
      if (state.holdStatus) await new Promise((resolve) => { state.releaseStatus = resolve; });
      const status = state.operationStatus ?? operation.status;
      return respond({ id: operation.id, conversation_id: operation.conversationId, status, manual_reconciliation_required: !["COMPLETED", "FAILED_SAFE", "CANCELLED"].includes(status), blind_retry_blocked: !["COMPLETED", "FAILED_SAFE", "CANCELLED"].includes(status) });
    }
    if (fulfillmentFixture && await fulfillmentFixture.handle({ key, requestWorkspace, respond, request })) return;
    const match = url.pathname.match(/^\/api\/v1\/direct\/conversations\/([^/]+)\/(.+)$/);
    if (match && scopedConversations.some((item) => item.id === match[1])) {
      const [, id, action] = match;
      if (request.method() === "GET" && action === "message-timeline") return respond([...Array.from({ length: 24 }, (_, index) => ({ id: `${id}-${index}`, conversation_id: id, direction: index % 2 ? "OUTBOUND" : "INBOUND", text: `Синтетичне повідомлення ${index + 1}`, received_at: "2026-10-19T10:00:00Z", delivery_status: index % 2 ? "PROVIDER_ACCEPTED" : "RECEIVED" })), ...state.extraTimeline.filter((message) => message.conversation_id === id)]);
      if (request.method() === "GET" && action === "customer-automation") return respond({ conversation_id: id, customer: null, linked_order_id: null, stage: "CUSTOMER_READY", missing_fields: [], can_create_order: true, profile_complete: false, created_automatically: false });
      if (request.method() === "GET" && action === "customer-data-extraction") return respond(null);
      if (request.method() === "GET" && action === "suggestions") {
        if (id === a) await suggestionsReady;
        return respond(id === a ? [{ id: "suggestion-a", title: "Чернетка", draft_text: "Пізня AI-чернетка", suggestion_type: "REPLY_DRAFT" }] : []);
      }
      if (request.method() === "POST" && action === "read") return respond({ ...scopedConversations.find((item) => item.id === id), unread_count: 0 });
      if (request.method() === "POST" && action === "reply/prepare") return state.prepareError ? respond({ detail: "Synthetic failure" }, 503) : respond({ ready: true, blockers: [], warnings: [], message_preview: JSON.parse(request.postData()).message_text });
      if (request.method() === "POST" && action === "reply/send") {
        if (state.abortSend) return route.abort("failed");
        if (state.holdSend) await new Promise((resolve) => { state.releaseSend = resolve; });
        const operationId = `33333333-3333-4333-8333-${String(++operationSequence).padStart(12, "0")}`;
        operations.set(operationId, { id: operationId, conversationId: id, workspaceId: requestWorkspace, status: state.sendStatus });
        if (state.appendSentTimeline && state.sendStatus === "COMPLETED") state.extraTimeline.push({ id: `synthetic-sent-${operationSequence}`, conversation_id: id, direction: "OUTBOUND", text: JSON.parse(request.postData()).message_text, received_at: "2026-10-19T10:01:00Z", delivery_status: "PROVIDER_ACCEPTED" });
        return respond({ operation_id: operationId, status: state.sendStatus, provider_message_id: state.sendStatus === "COMPLETED" ? "synthetic-provider-message" : null });
      }
      if (request.method() === "POST" && action === "analyze") return respond({});
    }
    if (request.method() === "GET" && ["/api/v1/orders", "/api/v1/products", "/api/v1/products/variants", "/api/v1/customers", "/api/v1/inventory", "/api/v1/advertising/campaigns"].includes(url.pathname)) return respond([]);
    if (key === "GET /api/v1/orders/dashboard") return respond({ revenue_today: 0, profit_today: 0, orders_today: 0 });
    if (key === "GET /api/v1/integrations/nova-poshta/readiness") return respond({ ready: false, can_create_ttn: false, blockers: [], warnings: [], missing_fields: [], checks: {} });
    unexpected.push(key);
    return respond({ detail: "Unexpected synthetic fixture request" }, 500);
  });
  const page = await context.newPage();
  fixturePages.push({ page, api, unexpected, errors });
  page.on("pageerror", (error) => errors.push(error.message));
  const card = (id) => page.locator(`[data-conversation-id="${id}"]`);
  const reply = () => page.getByRole("textbox", { name: "Відповідь менеджера" });
  const assertClean = async () => {
    expect(unexpected).toEqual([]);
    expect(errors).toEqual([]);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(2);
  };
  return { context, page, card, reply, api, state, assertClean };
}

try {
  if (!process.env.DIRECT_TEST_BASE_URL) {
    // The temporary listener proves the chosen port is free. If another process
    // wins the small close/spawn race, Next exits and the gate fails immediately.
    const port = await new Promise((resolve, reject) => {
      const probe = createServer();
      probe.once("error", reject);
      probe.listen(Number(process.env.DIRECT_TEST_PORT || 0), "127.0.0.1", () => {
        const address = probe.address();
        probe.close((error) => error ? reject(error) : resolve(address.port));
      });
    });
    base = `http://127.0.0.1:${port}`;
    origin = new URL(base).origin;
    let startupFailure;
    let startupOutput = "";
    server = spawn(process.execPath, [path.join(root, "frontend/node_modules/next/dist/bin/next"), "start", "-p", String(port), "--hostname", "127.0.0.1"], { cwd: path.join(root, "frontend"), stdio: ["ignore", "pipe", "pipe"] });
    server.once("error", (error) => { startupFailure = error; });
    server.once("exit", (code, signal) => { startupFailure = new Error(`Owned Next server exited early: code=${code}, signal=${signal}`); });
    server.stdout.on("data", (chunk) => { startupOutput += chunk.toString(); process.stdout.write(chunk); });
    server.stderr.on("data", (chunk) => process.stderr.write(chunk));
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt++) {
      if (startupFailure) throw startupFailure;
      // A successful login response alone cannot identify the process owner.
      if (startupOutput.includes("Ready in")) {
        try { if ((await fetch(`${base}/login`)).ok) { ready = true; break; } } catch {}
      }
      await new Promise((resolve) => setTimeout(resolve, 300));
    }
    if (startupFailure) throw startupFailure;
    if (!ready) throw new Error("Owned synthetic Next server did not become ready");
  }
  browser = await chromium.launch({ headless: true });
  const f = await fixture({ width: 1280, height: 900 }, { delayedSuggestions: true });
  await f.page.goto(`${base}/direct`);
  await expect(f.card(a)).toBeVisible();
  expect(f.api.filter((key) => key.startsWith("POST "))).toEqual([]);
  expect(f.api.some((key) => key.includes("message-timeline") || key.includes("customer-data-extraction"))).toBe(false);
  const search = f.page.getByRole("textbox", { name: "Пошук за іменем або нікнеймом" });
  await search.fill("@maria_fixture");
  await expect(f.card(b)).toBeVisible(); await expect(f.card(a)).toHaveCount(0);
  await search.fill("Олена"); await expect(f.card(a)).toBeVisible(); await expect(f.card(b)).toHaveCount(0);
  await search.fill("");
  const filters = f.page.getByRole("group", { name: "Фільтри діалогів" });
  await filters.getByRole("button", { name: /^Непрочитані/ }).click(); await expect(f.card(a)).toBeVisible(); await expect(f.card(b)).toHaveCount(0);
  await filters.getByRole("button", { name: /^Instagram/ }).click(); await expect(f.card(c)).toBeVisible(); await expect(f.card(b)).toHaveCount(0);
  await filters.getByRole("button", { name: /^Замовлення/ }).click(); await expect(f.card(a)).toBeVisible(); await expect(f.card(c)).toHaveCount(0);
  await search.fill("немає збігів"); await expect(f.page.getByText("Нічого не знайдено", { exact: true })).toBeVisible();
  await f.page.getByRole("button", { name: "Скинути фільтри" }).click(); await expect(f.card(b)).toBeVisible();
  expect(f.api.filter((key) => key.startsWith("POST "))).toEqual([]);
  await f.card(a).click(); await f.reply().fill("Чернетка Олени");
  f.state.releaseSuggestions();
  await f.page.getByRole("button", { name: "Відкрити AI-панель" }).click();
  await expect(f.page.getByRole("button", { name: "Вставити чернетку" })).toBeVisible();
  await f.page.keyboard.press("Escape");
  await expect(f.reply()).toHaveValue("Чернетка Олени");
  await f.reply().fill("");
  await f.page.getByRole("button", { name: "Оновити", exact: true }).click();
  await expect(f.reply()).toHaveValue("");
  await f.reply().fill("Чернетка Олени");
  f.state.prepareError = true;
  await f.page.getByRole("button", { name: "Перевірити відправлення", exact: true }).click();
  await expect(f.page.getByText("Не вдалося перевірити відправлення. Спробуйте ще раз.", { exact: true })).toBeVisible();
  f.state.prepareError = false;
  await f.reply().fill("Оновлена чернетка Олени");
  await expect(f.page.getByText("Не вдалося перевірити відправлення. Спробуйте ще раз.", { exact: true })).toHaveCount(0);
  await f.reply().fill("Чернетка Олени");
  await f.page.getByRole("button", { name: "Перевірити відправлення", exact: true }).click();
  await expect(f.page.getByText("Готово до ручного підтвердження", { exact: true })).toBeVisible();
  await f.card(b).click(); await expect(f.reply()).toHaveValue("");
  await expect(f.page.getByText("Готово до ручного підтвердження", { exact: true })).toHaveCount(0);
  await f.reply().fill("Чернетка Марії");
  await f.card(a).click(); await expect(f.reply()).toHaveValue("Чернетка Олени");
  f.state.holdSend = true;
  await f.page.getByRole("button", { name: "Підтвердити відправлення", exact: true }).click();
  await expect.poll(() => typeof f.state.releaseSend).toBe("function");
  await f.card(b).click(); await f.reply().fill("Нова чернетка Марії");
  f.state.releaseSend();
  await expect(f.reply()).toHaveValue("Нова чернетка Марії");
  await f.card(a).click(); await expect(f.reply()).toHaveValue("");
  await f.reply().fill("Нова відповідь");
  f.state.holdSend = false; f.state.sendStatus = "FAILED_SAFE";
  await f.page.getByRole("button", { name: "Підтвердити відправлення", exact: true }).click();
  await expect(f.page.getByText("Повідомлення не відправлено. Можна перевірити й повторити.", { exact: true })).toBeVisible();
  await expect(f.reply()).toHaveValue("Нова відповідь");
  f.state.sendStatus = "RETRY_PENDING";
  await f.page.getByRole("button", { name: "Підтвердити відправлення", exact: true }).click();
  await expect(f.page.getByRole("button", { name: "Підтвердити відправлення", exact: true })).toBeDisabled();
  await expect(f.reply()).toHaveValue("Нова відповідь");
  await f.page.screenshot({ path: path.join(output, "1280-list-thread.png"), fullPage: true });
  await f.assertClean(); await f.context.close();
  checks.push("search/name/username; all four filters/counts; filtered reset; no invisible first-thread requests; draft isolation; late AI; late COMPLETED; FAILED_SAFE and RETRY_PENDING");

  for (const width of [375, 390, 1440]) {
    for (const theme of width === 1440 ? ["light", "dark"] : ["light"]) {
      const m = await fixture({ width, height: width === 375 ? 812 : width === 390 ? 844 : 900 }, { theme });
      await m.page.goto(`${base}/direct`); await expect(m.card(a)).toBeVisible();
      if (width < 1024) {
        await expect(m.page.locator('.mobile-bottom-nav a[href="/direct"]')).toBeVisible();
        await expect(m.reply()).toHaveCount(0);
        if (width === 375) await m.page.screenshot({ path: path.join(output, "375-inbox.png"), fullPage: true });
      }
      await m.card(a).click(); await expect(m.reply()).toBeVisible();
      if (width < 1024) {
        // Bounds are checked before focus/fill/scroll and screenshots show only
        // the actual viewport, so focus scrolling cannot conceal bad density.
        const bounds = await m.page.evaluate(() => {
          const reply = document.querySelector('textarea');
          const send = [...document.querySelectorAll('button')].find((button) => button.textContent.trim() === "Підтвердити відправлення");
          const nav = document.querySelector('.mobile-bottom-nav');
          return { scrollY, replyTop: reply.getBoundingClientRect().top, replyBottom: reply.getBoundingClientRect().bottom, sendBottom: send.getBoundingClientRect().bottom, navTop: nav.getBoundingClientRect().top };
        });
        expect(bounds.scrollY).toBe(0);
        expect(bounds.replyTop).toBeGreaterThan(0);
        expect(bounds.replyBottom).toBeLessThan(bounds.navTop);
        expect(bounds.sendBottom).toBeLessThan(bounds.navTop);
        await m.page.screenshot({ path: path.join(output, `${width}-thread.png`), fullPage: false });
      }
      await m.reply().fill("Мобільна чернетка");
      if (width < 1024) {
        await expect(m.page.locator("[data-direct-list]")).toBeHidden();
        await m.page.getByRole("button", { name: "Назад до діалогів", exact: true }).click();
        // The same cached conversation recreates its pane with the same count.
        await m.card(a).click();
        await expect(m.page.locator("[data-direct-live-thread]").getByText("Синтетичне повідомлення 24", { exact: true })).toBeInViewport();
        await expect.poll(() => m.page.locator("[data-direct-live-thread]").evaluate((element) => element.scrollHeight - element.clientHeight - element.scrollTop)).toBeLessThan(4);
        await expect(m.reply()).toHaveValue("Мобільна чернетка");
        await m.page.getByRole("button", { name: "Назад до діалогів", exact: true }).click();
        await expect(m.card(b)).toBeVisible(); await m.card(b).click(); await expect(m.reply()).toHaveValue("");
        await m.page.getByRole("button", { name: "Назад до діалогів", exact: true }).click(); await m.card(a).click();
        await expect(m.reply()).toHaveValue("Мобільна чернетка");
      } else {
        await expect(m.page.locator("[data-direct-ai-panel]").first()).toBeVisible();
        await m.page.screenshot({ path: path.join(output, `1440-wide-ai-${theme}.png`), fullPage: true });
      }
      await m.assertClean();
      await m.page.getByRole("button", { name: "Створити замовлення", exact: true }).first().click();
      await expect(m.page).toHaveURL(/\/orders\?create=1/);
      await expect(m.page.getByRole("dialog")).toBeVisible();
      await m.page.keyboard.press("Escape"); await expect(m.page.getByRole("dialog")).toHaveCount(0);
      const fetchCount = m.api.filter((key) => key === "GET /api/v1/orders").length;
      await m.page.locator("main select").first().selectOption("NEW");
      await expect.poll(() => m.api.filter((key) => key === "GET /api/v1/orders").length).toBeGreaterThan(fetchCount);
      await expect(m.page.getByRole("dialog")).toHaveCount(0);
      await m.page.getByRole("button", { name: "Створити замовлення", exact: true }).first().click();
      await expect(m.page.getByRole("dialog")).toBeVisible();
      await m.page.keyboard.press("Escape");
      await expect(m.page.getByRole("dialog")).toHaveCount(0);
      await m.assertClean(); await m.context.close();
      checks.push(`${width}/${theme}: layout, overflow, mobile selection/back, quick create/close/refetch/repeated explicit create`);
    }
  }

  for (const status of ["RECONCILIATION_REQUIRED", "UNKNOWN"]) {
    const s = await fixture({ width: 1280, height: 900 });
    await s.page.goto(`${base}/direct?conversation=${a}`); await s.reply().fill("Збережіть цю чернетку");
    s.state.sendStatus = status;
    await s.page.getByRole("button", { name: "Підтвердити відправлення", exact: true }).click();
    await expect(s.page.getByRole("button", { name: "Підтвердити відправлення", exact: true })).toBeDisabled();
    await expect(s.reply()).toHaveValue("Збережіть цю чернетку");
    await s.reply().fill("Змінена чернетка");
    await expect(s.page.getByRole("button", { name: "Підтвердити відправлення", exact: true })).toBeDisabled();
    await s.page.reload(); await s.reply().fill("Після перезавантаження");
    await expect(s.page.getByRole("button", { name: "Підтвердити відправлення", exact: true })).toBeDisabled();
    await s.assertClean(); await s.context.close(); checks.push(`${status}: draft retained, blind retry blocked after edits/reload`);
  }

  for (const terminal of ["COMPLETED", "FAILED_SAFE", "CANCELLED"]) {
    const r = await fixture({ width: 1280, height: 900 });
    await r.page.goto(`${base}/direct?conversation=${a}`); await r.reply().fill("Початкова чернетка");
    r.state.sendStatus = "RETRY_PENDING";
    await r.page.getByRole("button", { name: "Підтвердити відправлення", exact: true }).click();
    await expect.poll(() => r.state.statusRequests).toBeGreaterThan(0);
    await expect(r.page.getByRole("button", { name: "Оновити стан відправлення" })).toBeEnabled();
    for (const pending of ["PREPARED", "SENDING", "PROVIDER_SUCCEEDED", "RETRY_PENDING", "RECONCILIATION_REQUIRED"]) {
      r.state.operationStatus = pending;
      await r.page.getByRole("button", { name: "Оновити стан відправлення" }).click();
      await expect(r.page.getByRole("button", { name: "Оновити стан відправлення" })).toBeEnabled();
      await expect(r.page.getByRole("button", { name: "Підтвердити відправлення", exact: true })).toBeDisabled();
      await expect(r.reply()).toHaveValue("Початкова чернетка");
    }
    // Switching threads cannot let the recovered result touch B's composer.
    await r.card(b).click(); await r.reply().fill("Чернетка іншого діалогу");
    r.state.operationStatus = terminal;
    await r.card(a).click();
    await expect(r.page.getByRole("button", { name: "Оновити стан відправлення" })).toHaveCount(0);
    await expect(r.reply()).toHaveValue(terminal === "COMPLETED" ? "" : "Початкова чернетка");
    if (terminal !== "COMPLETED") await expect(r.page.getByRole("button", { name: "Підтвердити відправлення", exact: true })).toBeEnabled();
    await r.card(b).click(); await expect(r.reply()).toHaveValue("Чернетка іншого діалогу");
    await r.assertClean(); await r.context.close(); checks.push(`operation GET recovery: pending statuses stay blocked; ${terminal} settles only owning thread/revision`);
  }

  const recovery = await fixture({ width: 1280, height: 900 });
  await recovery.page.goto(`${base}/direct?conversation=${a}`); await recovery.reply().fill("Надіслана чернетка");
  recovery.state.sendStatus = "RECONCILIATION_REQUIRED";
  await recovery.page.getByRole("button", { name: "Підтвердити відправлення", exact: true }).click();
  await expect.poll(() => recovery.state.statusRequests).toBeGreaterThan(0);
  await expect(recovery.page.getByRole("button", { name: "Оновити стан відправлення" })).toBeEnabled();
  // Delayed completion in the same editor must preserve a newer revision.
  await recovery.reply().fill("Новіша чернетка");
  recovery.state.operationStatus = "COMPLETED";
  await recovery.page.getByRole("button", { name: "Оновити стан відправлення" }).click();
  await expect(recovery.page.getByRole("button", { name: "Підтвердити відправлення", exact: true })).toBeEnabled();
  await expect(recovery.reply()).toHaveValue("Новіша чернетка");
  recovery.state.operationStatus = null;
  await recovery.page.getByRole("button", { name: "Підтвердити відправлення", exact: true }).click();
  await expect(recovery.page.getByRole("button", { name: "Оновити стан відправлення" })).toBeEnabled();
  recovery.state.holdStatus = true;
  await recovery.page.goto(`${base}/orders`);
  await recovery.page.goto(`${base}/direct?conversation=${a}`);
  await expect.poll(() => typeof recovery.state.releaseStatus).toBe("function");
  await recovery.reply().fill("Чернетка нового редактора");
  recovery.state.operationStatus = "COMPLETED"; recovery.state.holdStatus = false; recovery.state.releaseStatus();
  await expect(recovery.page.getByRole("button", { name: "Оновити стан відправлення" })).toHaveCount(0);
  await expect(recovery.reply()).toHaveValue("Чернетка нового редактора");
  await expect(recovery.page.getByRole("button", { name: "Підтвердити відправлення", exact: true })).toBeEnabled();
  await recovery.assertClean(); await recovery.context.close(); checks.push("delayed GET COMPLETED preserves newer revision and post-remount draft");

  const lost = await fixture({ width: 1280, height: 900 });
  await lost.page.goto(`${base}/direct?conversation=${a}`); await lost.reply().fill("Втрачена відповідь сервера");
  lost.state.abortSend = true;
  await lost.page.getByRole("button", { name: "Підтвердити відправлення", exact: true }).click();
  await expect(lost.page.getByText(/Сервер не підтвердив результат. Перевірте повідомлення/)).toBeVisible();
  await expect(lost.page.getByRole("button", { name: "Оновити стан відправлення" })).toHaveCount(0);
  await expect(lost.page.getByRole("button", { name: "Підтвердити відправлення", exact: true })).toBeDisabled();
  await lost.page.reload(); await lost.reply().fill("Без повтору");
  await expect(lost.page.getByRole("button", { name: "Підтвердити відправлення", exact: true })).toBeDisabled();
  expect(lost.state.statusRequests).toBe(0);
  await lost.assertClean(); await lost.context.close(); checks.push("unknown without operation ID: honest help, no invented recovery, no blind retry after reload");

  const tenant = await fixture({ width: 1280, height: 900 }, { multiWorkspace: true });
  await tenant.page.goto(`${base}/direct?conversation=${a}`); await tenant.reply().fill("Чернетка першого магазину");
  tenant.state.holdSend = true;
  await tenant.page.getByRole("button", { name: "Підтвердити відправлення", exact: true }).click();
  await expect.poll(() => typeof tenant.state.releaseSend).toBe("function");
  await tenant.page.locator('.account-profile-trigger').click();
  await tenant.page.getByRole("button", { name: /Другий синтетичний магазин/ }).click();
  await tenant.card(d).click(); await tenant.reply().fill("Чернетка другого магазину");
  tenant.state.releaseSend();
  await expect(tenant.reply()).toHaveValue("Чернетка другого магазину");
  await tenant.page.locator('.account-profile-trigger').click();
  await tenant.page.getByRole("button", { name: /^Синтетичний магазин/ }).click();
  await tenant.card(a).click(); await expect(tenant.reply()).toHaveValue("");
  await tenant.assertClean(); await tenant.context.close(); checks.push("late COMPLETED keeps workspace ownership and leaves another workspace draft intact");

  const analyst = await fixture({ width: 1440, height: 900 }, { role: "ANALYST" });
  await analyst.page.goto(`${base}/direct?conversation=${c}`);
  await expect(analyst.reply()).toBeDisabled();
  await expect(analyst.page.getByRole("button", { name: "Проаналізувати діалог" }).first()).toBeDisabled();
  await expect(analyst.page.getByRole("button", { name: "Перевірити відправлення" })).toBeDisabled();
  await expect(analyst.page.getByRole("button", { name: "Підтвердити відправлення" })).toBeDisabled();
  await analyst.page.goto(`${base}/orders?create=1`); await expect(analyst.page.getByRole("dialog")).toHaveCount(0);
  expect(analyst.api.filter((key) => key.startsWith("POST "))).toEqual([]);
  await analyst.assertClean(); await analyst.context.close(); checks.push("analyst write controls and quick-create permission");
  await runFulfillmentScenarios({ fixture, base, expect, a, b, workspaceId, output, checks });
  console.log(`Direct synthetic browser gate passed (${checks.length} scenarios).`);
} catch (error) {
  failures.push(error.stack || String(error));
  // Only pages created by the fail-closed synthetic fixture are eligible.
  let index = 0;
  for (const { page, api, unexpected, errors } of fixturePages) {
    if (page.isClosed() || !page.url().startsWith(origin + "/")) continue;
    try {
      const prefix = `failure-${++index}`;
      await page.screenshot({ path: path.join(output, `${prefix}.png`), fullPage: false, timeout: 5000 });
      await writeFile(path.join(output, `${prefix}.json`), JSON.stringify({
        syntheticOnly: true, url: page.url(), api: api.slice(-60), unexpected, errors,
        body: (await page.locator("body").innerText({ timeout: 3000 })).slice(0, 12000),
      }, null, 2));
    } catch (captureError) { failures.push(`Synthetic failure capture: ${captureError.message}`); }
  }
  throw error;
} finally {
  await writeFile(path.join(output, "result.json"), JSON.stringify({ syntheticOnly: true, checks, failures }, null, 2));
  await browser?.close();
  server?.kill("SIGTERM");
}
