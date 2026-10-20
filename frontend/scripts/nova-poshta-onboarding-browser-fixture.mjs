// Synthetic only. Install on an authenticated OWNER page before navigating.
export async function installNovaPoshtaOnboardingFixture(page) {
  const state = { payloads: [], failLookup: false, settings: { status: "DISCONNECTED", masked_api_key: null, environment_capability: false, workspace_permission: false, provider_writes_enabled: false, sender_configured: false, connection_verified: false } };
  const senders = [{ ref: "synthetic-sender-a", description: "Магазин Тест А" }, { ref: "synthetic-sender-b", description: "Магазин Тест Б" }];
  await page.route("**/integrations/nova-poshta/**", async route => {
    const request = route.request(), url = new URL(request.url());
    const endpoint = url.pathname.split("/").at(-1);
    const respond = (json, status = 200) => route.fulfill({ status, json });
    if (request.method() === "POST" && endpoint === "settings") {
      const payload = request.postDataJSON(); state.payloads.push(payload);
      const { api_key, ...sender } = payload;
      const changed = Boolean(api_key) || Object.entries(sender).some(([key, value]) => value !== state.settings[key]);
      state.settings = { ...state.settings, ...sender, status: "CONNECTED", masked_api_key: "********test", sender_configured: Object.values(sender).every(Boolean), connection_verified: changed ? false : state.settings.connection_verified, workspace_permission: false };
      return respond(state.settings);
    }
    if (endpoint === "test-connection") {
      state.settings.connection_verified = state.settings.sender_configured;
      return respond({ success: state.settings.connection_verified, status: "CONNECTED", errors: [], message: "Synthetic verification" });
    }
    if (endpoint === "settings") return respond(state.settings);
    if (state.failLookup) return respond({ detail: "NOVA_POSHTA_SENDER_LOOKUP_UNAVAILABLE" }, 400);
    if (endpoint === "senders") return respond(senders);
    if (endpoint === "sender-contacts") return respond([{ ref: `${url.searchParams.get("sender_ref")}-contact`, description: "Олена Тестова" }]);
    if (endpoint === "cities") return respond([{ ref: "synthetic-city", description: "Київ" }]);
    if (endpoint === "warehouses") return respond([{ ref: "synthetic-warehouse", description: "Відділення №1", number: "1" }]);
    throw new Error(`Unexpected provider operation in read-only onboarding fixture: ${endpoint}`);
  });
  return state;
}

// Runner supplies authenticated OWNER page, Playwright expect, base URL, viewport.
export async function runNovaPoshtaOnboardingScenario({ page, expect, base, width }) {
  await page.setViewportSize({ width, height: 900 });
  const state = await installNovaPoshtaOnboardingFixture(page);
  const ready = page.waitForResponse(response => response.url().endsWith("/integrations/nova-poshta/settings") && response.request().method() === "GET");
  await page.goto(`${base}/settings/integrations`);
  await ready;
  const card = page.locator("section").filter({ has: page.getByRole("heading", { name: "Нова Пошта", exact: true }) }).first();
  await expect(card.getByRole("link", { name: "Відкрити налаштування безпеки Нової пошти" })).toHaveAttribute("href", "https://new.novaposhta.ua/dashboard/settings/developers");
  const password = card.locator('input[type="password"]');
  await password.fill("synthetic-key-test");
  await card.getByRole("button", { name: "Зберегти API-ключ", exact: true }).click();
  await expect(password).toHaveValue("");
  await card.getByLabel("Відправник", { exact: true }).selectOption("synthetic-sender-a");
  await card.getByLabel("Контактна особа", { exact: true }).selectOption("synthetic-sender-a-contact");
  await card.getByLabel("Відправник", { exact: true }).selectOption("synthetic-sender-b");
  await expect(card.getByLabel("Контактна особа", { exact: true })).toHaveValue("");
  await card.getByLabel("Контактна особа", { exact: true }).selectOption("synthetic-sender-b-contact");
  await card.getByPlaceholder("Пошук міста Нової Пошти").fill("Ки");
  await card.getByRole("button", { name: "Київ", exact: true }).click();
  await card.getByRole("button", { name: "Відділення №1", exact: true }).click();
  await card.getByLabel("Телефон відправника", { exact: true }).fill("0671234567");
  await card.getByRole("button", { name: "Зберегти відправника", exact: true }).click();
  expect(state.payloads.at(-1)).toMatchObject({ api_key: null, sender_counterparty_ref: "synthetic-sender-b", sender_contact_ref: "synthetic-sender-b-contact", sender_city_ref: "synthetic-city", sender_warehouse_ref: "synthetic-warehouse" });
  await card.getByRole("button", { name: "Перевірити підключення", exact: true }).click();
  expect(state.settings.workspace_permission).toBe(false);
  expect(state.settings.provider_writes_enabled).toBe(false);
  expect(await page.evaluate(() => [localStorage, sessionStorage].some(storage => Object.values(storage).some(value => value.includes("synthetic-key-test"))))).toBe(false);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  return state;
}
