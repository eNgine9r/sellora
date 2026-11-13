import { expect, test, type Page } from "@playwright/test";

const prefix = "/api/v1/platform-admin";

async function signIn(page: Page, account: "admin" | "owner") {
  await page.goto("/platform-admin");
  await expect(page.getByRole("heading", { name: "Вхід до Platform Admin" })).toBeVisible();
  await page.getByLabel("Email").fill(`qa-platform-${account}@example.com`);
  await page.getByLabel("Пароль").fill("QA-Platform-Local123!");
  await page.getByRole("button", { name: "Увійти", exact: true }).click();
}

test("admin views real metrics, filters, pages and opens a workspace profile", async ({ page, isMobile }) => {
  const errors: string[] = [];
  const platformHeaders: Record<string, string>[] = [];
  const directoryRequests: { method: string; search: string; body: string | null }[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith(prefix)) platformHeaders.push(request.headers());
    if (url.pathname === `${prefix}/workspaces/search`) {
      directoryRequests.push({ method: request.method(), search: url.search, body: request.postData() });
    }
  });
  const summaryResponse = page.waitForResponse((response) => new URL(response.url()).pathname === `${prefix}/summary` && response.ok());
  await signIn(page, "admin");
  const summary = await (await summaryResponse).json();
  await expect(page.getByRole("heading", { name: "Керування платформою" })).toBeVisible();
  await expect(page.getByTestId("total_workspaces")).toHaveText(String(summary.total_workspaces));
  await expect(page.getByTestId("workspaces_with_current_term")).toHaveText(String(summary.workspaces_with_current_term));
  expect(summary.workspaces_with_current_term).toBeGreaterThan(0);
  const activityOrders = page.getByTestId("activity-orders_created");
  await expect(activityOrders).toHaveText("1");
  await page.getByRole("button", { name: "30 днів", exact: true }).click();
  await expect(activityOrders).toHaveText("2");
  await expect(page.getByRole("button", { name: "30 днів", exact: true })).toHaveAttribute("aria-pressed", "true");
  const navigation = page.getByRole("navigation", { name: "Розділи панелі" });
  await navigation.getByRole("link", { name: "Активність" }).click();
  await expect(page).toHaveURL(/#platform-activity$/);
  await page.getByText("Переглянути значення за днями").click();
  await expect(page.getByRole("table", { name: "Замовлення за днями" }).getByRole("row")).toHaveCount(31);
  await page.getByText("Переглянути значення за днями").click();
  await navigation.getByRole("link", { name: "Магазини" }).click();
  await expect(page).toHaveURL(/#platform-directory$/);

  await page.getByRole("textbox", { name: "Пошук" }).fill("QA Platform Shop");
  await page.getByRole("button", { name: "Застосувати" }).click();
  const row = page.getByRole("button", { name: "Відкрити магазин QA Platform Shop 22" });
  await expect(row).toBeVisible();
  await expect(isMobile ? page.getByRole("list", { name: "Реєстр магазинів" }) : page.getByRole("table", { name: "Реєстр магазинів" })).toBeVisible();
  await page.getByRole("button", { name: "Далі" }).click();
  await expect(page.getByText("Сторінка 2")).toBeVisible();
  await expect(page.getByRole("button", { name: "Відкрити магазин QA Platform Shop 01" })).toBeVisible();
  await expect(row).toHaveCount(0);
  await page.getByRole("button", { name: "Назад" }).click();
  await row.click();

  const profile = page.getByRole("dialog", { name: "QA Platform Shop 22" });
  await expect(profile.getByText("qa-pilot")).toBeVisible();
  await expect(profile.getByText("Початок періоду (UTC)")).toBeVisible();
  await expect(profile.getByText("Активні учасники команди")).toBeVisible();
  await expect(profile.getByText("Активні учасники команди").locator("xpath=following-sibling::dd[1]")).toHaveText("1");
  await expect(profile.getByTestId("activity-orders_created")).toHaveText("1");
  await profile.getByRole("button", { name: "30 днів", exact: true }).click();
  await expect(profile.getByTestId("activity-orders_created")).toHaveText("1");
  await expect(profile.getByText(/@example\.com/)).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(profile).toHaveCount(0);
  await expect(row).toBeFocused();

  await page.getByLabel("Статус підписки").selectOption("ACTIVE");
  await page.getByRole("button", { name: "Застосувати" }).click();
  await expect(page.getByText("На сторінці: 1", { exact: true })).toBeVisible();
  await expect(row).toBeVisible();
  await expect(page.getByRole("button", { name: "Далі", exact: true })).toHaveCount(0);
  await page.getByLabel("Статус підписки").selectOption("");
  await page.getByLabel("Тип магазину").selectOption("true");
  await page.getByRole("button", { name: "Застосувати" }).click();
  await expect(page.getByRole("button", { name: "Відкрити магазин QA Platform Shop 01" })).toBeVisible();
  await expect(row).toHaveCount(0);
  await page.getByRole("textbox", { name: "Пошук" }).fill("Missing Platform Fixture");
  await page.getByRole("button", { name: "Застосувати" }).click();
  await expect(page.getByRole("heading", { name: "Магазинів не знайдено" })).toBeVisible();

  const workspaces = (url: URL) => url.pathname === `${prefix}/workspaces/search`;
  await page.route(workspaces, (route) => route.fulfill({ status: 503, body: "{}" }), { times: 1 });
  await page.getByRole("button", { name: "Скинути" }).click();
  await expect(page.getByRole("heading", { name: "Не вдалося завантажити дані" })).toBeVisible();
  await page.getByRole("button", { name: "Спробувати ще раз" }).click();
  await expect(row).toBeVisible();

  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(platformHeaders.length).toBeGreaterThan(4);
  expect(platformHeaders.every((headers) => !("x-workspace-id" in headers))).toBe(true);
  expect(directoryRequests.length).toBeGreaterThan(3);
  expect(directoryRequests.every(({ method, search }) => method === "POST" && search === "")).toBe(true);
  expect(directoryRequests.some(({ body }) => body && JSON.parse(body).q === "QA Platform Shop")).toBe(true);
  expect(directoryRequests.some(({ body }) => body && JSON.parse(body).cursor)).toBe(true);
  expect(directoryRequests.some(({ body }) => body && JSON.parse(body).subscription_status === "ACTIVE")).toBe(true);
  const authorization = platformHeaders.find((headers) => headers.authorization)?.authorization;
  expect(authorization).toBeTruthy();
  const legacyAlias = await page.request.get(`${prefix}/workspaces/`, {
    headers: { authorization: authorization! },
    params: { q: "synthetic-proxy-private-marker" },
    maxRedirects: 0,
  });
  expect(legacyAlias.status()).toBe(422);
  expect(legacyAlias.headers().location).toBeUndefined();
  expect(await legacyAlias.text()).not.toContain("synthetic-proxy-private-marker");
  const ordinarySlash = await page.request.get("/platform-admin/", { maxRedirects: 0 });
  expect(ordinarySlash.status()).toBe(308);
  expect(ordinarySlash.headers().location).toBe("/platform-admin");

  expect(errors).toEqual([]);
});

test("a tenant owner is denied through the direct URL and never loads platform data", async ({ page }) => {
  const paths: string[] = [];
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (path.startsWith(prefix)) paths.push(path);
  });
  const denied = page.waitForResponse((response) => new URL(response.url()).pathname === `${prefix}/me` && response.status() === 403);
  await signIn(page, "owner");
  await denied;
  await expect(page.getByRole("heading", { name: "Доступ заборонено" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Реєстр магазинів" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Користувачі" })).toHaveCount(0);
  expect(paths).toEqual([`${prefix}/me`]);
});

test("admin finds a Sellora account and can archive and restore an eligible workspace", async ({ page }) => {
  await signIn(page, "admin");
  const sections = page.getByRole("navigation", { name: "Розділи панелі" });
  await sections.getByRole("link", { name: "Користувачі" }).click();
  await page.getByRole("textbox", { name: "Ім’я, email або ID" }).fill("qa-platform-owner@example.com");
  await page.getByRole("button", { name: "Показати користувачів" }).click();
  await page.getByRole("button", { name: "Відкрити профіль QA Owner" }).click();
  const user = page.getByRole("dialog", { name: "QA Owner" });
  await expect(user.getByText("QA Platform Shop 22")).toBeVisible();
  await expect(user.getByText("Власник", { exact: true })).toBeVisible();
  await user.getByRole("button", { name: "Деталі", exact: true }).click();
  const paid = page.getByRole("dialog", { name: "QA Platform Shop 22" });
  await expect(paid.getByText("qa-pilot")).toBeVisible();
  await expect(paid.getByRole("button", { name: "Архівувати магазин" })).toHaveCount(0);
  await page.keyboard.press("Escape");

  await sections.getByRole("link", { name: "Магазини" }).click();
  await page.getByRole("textbox", { name: "Пошук", exact: true }).fill("QA Platform Shop 01");
  const directory = page.getByRole("region", { name: "Реєстр магазинів" });
  await directory.getByRole("button", { name: "Застосувати" }).click();
  const open = directory.getByRole("button", { name: "Відкрити магазин QA Platform Shop 01" });
  await open.click();
  const demo = page.getByRole("dialog", { name: "QA Platform Shop 01" });
  await demo.getByRole("button", { name: "Архівувати магазин" }).click();
  await demo.getByRole("button", { name: "Підтвердити архівацію" }).click();
  await expect(demo.getByRole("button", { name: "Відновити з архіву" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(open).toHaveCount(0);
  await directory.getByRole("button", { name: /^Архів/ }).click();
  await open.click();
  await demo.getByRole("button", { name: "Відновити з архіву" }).click();
  await demo.getByRole("button", { name: "Підтвердити відновлення" }).click();
  await expect(demo.getByRole("button", { name: "Архівувати магазин" })).toBeVisible();
  await expect(demo.getByText("Вимкнений", { exact: true })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(open).toHaveCount(0);
  await directory.getByRole("button", { name: "Поточний реєстр" }).click();
  await expect(open).toBeVisible();
});
