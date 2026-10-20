import path from "node:path";

export async function runDirectLeadScenarios({ fixture, base, expect, a, output, checks }) {
  for (const width of [1280, 375]) {
    const f = await fixture({ width, height: width < 1024 ? 812 : 900 });
    await f.page.goto(`${base}/direct?conversation=${a}`);
    const panel = f.page.locator("[data-direct-customer-automation]");
    await expect(panel.getByRole("button", { name: "Створити лід", exact: true })).toBeVisible();
    await panel.getByRole("button", { name: "Створити лід", exact: true }).click();
    await expect(panel.getByText("Лід прив’язано до цього діалогу", { exact: true })).toBeVisible();
    await expect(panel.getByRole("button", { name: "Створити лід", exact: true })).toHaveCount(0);
    await expect(panel.getByRole("link", { name: "Переглянути ліди" })).toBeVisible();
    await f.page.reload();
    await expect(panel.getByText("Лід прив’язано до цього діалогу", { exact: true })).toBeVisible();
    expect(f.api.filter((key) => key.endsWith("/lead/ensure"))).toHaveLength(1);
    expect(f.api.filter((key) => /^POST .*\/(orders|shipments|send)$/.test(key))).toEqual([]);
    await f.page.screenshot({ path: path.join(output, `lead-linked-${width}.png`), fullPage: false });
    await f.assertClean(); await f.context.close();
    checks.push(`Direct lead create/reload/no implicit order or send at ${width}px`);
  }

  const failed = await fixture({ width: 1280, height: 900 });
  failed.state.leadFailure = true;
  await failed.page.goto(`${base}/direct?conversation=${a}`);
  await failed.page.getByRole("button", { name: "Створити лід", exact: true }).click();
  await expect(failed.page.getByText("Не вдалося створити лід. Потрібне вхідне повідомлення з Instagram.", { exact: true })).toBeVisible();
  await expect(failed.page.getByRole("button", { name: "Створити лід", exact: true })).toBeEnabled();
  await failed.assertClean(); await failed.context.close();
  checks.push("Direct lead failure is recoverable and does not pretend success");

  const repeat = await fixture({ width: 375, height: 812 });
  repeat.state.repeatSale = true;
  repeat.state.leadLinked = true;
  await repeat.page.goto(`${base}/direct?conversation=${a}`);
  await expect(repeat.page.getByRole("link", { name: "Створити ще замовлення" })).toHaveAttribute("href", /create=1.*direct_conversation_id=/);
  await expect(repeat.page.getByRole("link", { name: "Відкрити замовлення", exact: true })).toHaveAttribute("href", /order_id=88888888/);
  expect(repeat.api.filter((key) => key.startsWith("POST ") && !key.endsWith("/read"))).toEqual([]);
  await repeat.assertClean(); await repeat.context.close();
  checks.push("Repeat opportunity offers a fresh wizard and retains previous order without order creation");

  const analyst = await fixture({ width: 375, height: 812 }, { role: "ANALYST" });
  analyst.state.repeatSale = true;
  await analyst.page.goto(`${base}/direct?conversation=${a}`);
  await expect(analyst.page.getByRole("button", { name: "Створити лід", exact: true })).toHaveCount(0);
  await expect(analyst.page.getByRole("link", { name: "Створити ще замовлення" })).toHaveCount(0);
  expect(analyst.api.filter((key) => key.startsWith("POST "))).toEqual([]);
  await analyst.assertClean(); await analyst.context.close();
  checks.push("Analyst has no Lead or repeat-order mutation action");
}
