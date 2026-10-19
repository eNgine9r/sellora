import path from "node:path";

export async function runFulfillmentScenarios({ fixture, base, expect, a, b, workspaceId, output, checks }) {
  const handoff = "Підготувати повідомлення з ТТН";
  const noSend = (f) => expect(f.api.filter((key) => /reply\/(send|prepare)$/.test(key))).toEqual([]);
  const full = await fixture({ width: 1280, height: 900 }, { fulfillment: true });
  const ff = full.state.fulfillment;
  await full.page.goto(`${base}/direct?conversation=${a}`);
  await full.reply().fill("Моя невідправлена чернетка");
  const header = full.page.getByRole("button", { name: "Клієнт і замовлення", exact: true });
  await expect(header).toBeVisible();
  await header.click();
  await full.page.getByRole("link", { name: "Оформити замовлення", exact: true }).click();
  let wizard = full.page.getByRole("dialog");
  await expect(wizard).toBeVisible();
  await wizard.getByLabel("Місто", { exact: true }).fill("Ки");
  await wizard.getByRole("button", { name: "Київ", exact: true }).click();
  await wizard.getByRole("button", { name: "Відділення №1", exact: true }).click();
  await wizard.getByRole("button", { name: "Продовжити", exact: true }).click();
  const variant = wizard.getByRole("combobox", { name: /^Товар і варіант/ });
  await expect(variant).toBeVisible();
  await variant.selectOption(ff.variantId);
  await wizard.getByLabel("Кількість", { exact: true }).fill("3");
  const cost = () => wizard.getByLabel("Собівартість", { exact: true });
  for (const invalid of ["-1", "", "1e309"]) {
    await cost().fill(invalid);
    await wizard.getByRole("button", { name: "Продовжити", exact: true }).click();
    await expect(wizard.getByRole("alert")).toContainText("собівартість");
    expect(ff.state.payloads).toHaveLength(0);
  }
  await cost().fill("40");
  await wizard.getByText("Додаткові деталі (необов’язково)", { exact: true }).click();
  for (const [label, value] of [["Доставка", "5"], ["Витрати на рекламу", "10"], ["Комісія COD", "2"], ["Інші витрати", "3"]]) {
    await wizard.getByLabel(label, { exact: true }).fill(value);
  }
  await wizard.getByRole("button", { name: "Продовжити", exact: true }).click();
  const money = (selector, value) => expect(wizard.locator(selector)).toContainText(new RegExp(`${value}[,.]00`));
  await money("[data-fulfillment-product-cost]", 120);
  await money("[data-fulfillment-other-costs]", 20);
  await money("[data-fulfillment-total-costs]", 140);
  await money("[data-fulfillment-profit]", 160);
  await wizard.getByRole("button", { name: "Назад", exact: true }).click();
  await expect(cost()).toHaveValue("40");
  await expect(wizard.getByLabel("Кількість", { exact: true })).toHaveValue("3");
  await cost().fill("0");
  await wizard.getByRole("button", { name: "Продовжити", exact: true }).click();
  await expect(wizard.getByText(/Оцінка неповна/)).toBeVisible();
  await money("[data-fulfillment-profit]", 280);
  await wizard.getByRole("button", { name: "Назад", exact: true }).click();
  await cost().fill("40");
  await wizard.getByRole("button", { name: "Продовжити", exact: true }).click();
  await full.page.screenshot({ path: path.join(output, "fulfillment-review-1280.png"), fullPage: true });
  await wizard.getByRole("button", { name: "Створити замовлення і ТТН", exact: true }).click();
  await expect(wizard.getByRole("link", { name: handoff })).toBeVisible();
  expect(ff.state.payloads).toHaveLength(1);
  expect(ff.state.payloads[0]).toMatchObject({ customer_id: ff.customerId, items: [{ product_variant_id: ff.variantId, quantity: 3, unit_price: 100, unit_cost: 40 }], shipping_cost: 5, ad_cost: 10, cod_fee: 2, other_cost: 3, create_ttn: true });
  await expect(wizard.getByRole("link", { name: "Відкрити відправлення", exact: true })).toHaveAttribute("href", `/shipments?shipment_id=${ff.shipmentId}`);
  await wizard.getByRole("link", { name: "Відкрити відправлення", exact: true }).click();
  await expect(full.page.getByRole("link", { name: handoff, exact: true })).toBeVisible();
  await expect(full.page.getByRole("dialog").getByRole("heading", { name: "Створити відправлення", exact: true })).toHaveCount(0);
  await full.page.getByRole("link", { name: handoff, exact: true }).click();
  await expect(full.reply()).toHaveValue("Моя невідправлена чернетка");
  await expect(full.page.locator("[data-direct-ttn-draft]")).toContainText("20400000000000");
  noSend(full);
  await full.page.getByRole("button", { name: "Вставити в чернетку", exact: true }).click();
  await expect(full.page.getByRole("dialog", { name: "Замінити поточну чернетку?" })).toBeVisible();
  await full.page.getByRole("button", { name: "Скасувати", exact: true }).click();
  await expect(full.reply()).toHaveValue("Моя невідправлена чернетка");
  await full.page.getByRole("button", { name: "Вставити в чернетку", exact: true }).click();
  await full.page.getByRole("button", { name: "Замінити чернетку", exact: true }).click();
  await expect(full.reply()).toHaveValue("Для замовлення SYN-1001 створено накладну Нової пошти: 20400000000000.");
  noSend(full);
  // Navigation/insertion never sends. Only this explicit manager click may send.
  // New inbound and sent timeline rows must resume ordinary newest-message scroll.
  full.state.extraTimeline.push({ id: "synthetic-inbound-after-ttn", conversation_id: a, direction: "INBOUND", text: "Нове вхідне після ТТН", received_at: "2026-10-19T10:01:00Z", delivery_status: "RECEIVED" });
  const pane = full.page.locator("[data-direct-live-thread]");
  await expect(full.page.getByText("Нове вхідне після ТТН", { exact: true })).toBeInViewport({ timeout: 10000 });
  await expect.poll(() => pane.evaluate((element) => element.scrollHeight - element.clientHeight - element.scrollTop)).toBeLessThan(4);
  full.state.appendSentTimeline = true;
  await full.page.getByRole("button", { name: "Підтвердити відправлення", exact: true }).click();
  await expect(full.reply()).toHaveValue("");
  await expect(pane.getByText("Для замовлення SYN-1001 створено накладну Нової пошти: 20400000000000.", { exact: true })).toBeInViewport({ timeout: 10000 });
  await expect.poll(() => pane.evaluate((element) => element.scrollTop)).toBeGreaterThan(100);
  expect(full.api.filter((key) => /reply\/send$/.test(key))).toHaveLength(1);
  expect(full.api.filter((key) => /reply\/prepare$/.test(key))).toHaveLength(0);
  expect(ff.state.readWorkspaces.every((id) => id === workspaceId)).toBe(true);
  await full.assertClean(); await full.context.close();
  checks.push("post-TTN new inbound and explicit sent timeline rows stay visible at newest-message scroll; no persistent handoff-to-top mode");
  checks.push("fulfillment: cost × quantity, invalid/negative/nonfinite costs, zero-cost estimate, step persistence, review totals and actual payload; wizard -> existing shipment -> verified TTN; manual draft survives route and requires confirmation; no send/prepare on navigation");

  for (const manualHeader of [false, true]) {
    const delayed = await fixture({ width: 375, height: 812 }, { fulfillment: true });
    delayed.state.holdAutomation = true;
    await delayed.page.goto(`${base}/direct?conversation=${a}`);
    await expect.poll(() => typeof delayed.state.releaseAutomation).toBe("function");
    const pane = delayed.page.locator("[data-direct-live-thread]");
    const latest = pane.getByText("Синтетичне повідомлення 24", { exact: true });
    await expect(latest).toBeInViewport();
    const initialHeight = await pane.evaluate((element) => element.scrollHeight);
    if (manualHeader) {
      await delayed.page.getByRole("button", { name: "Клієнт і замовлення", exact: true }).click();
      await expect.poll(() => pane.evaluate((element) => element.scrollTop)).toBe(0);
    }
    delayed.state.holdAutomation = false;
    delayed.state.releaseAutomation();
    // Release the actual customer card; its existing extraction portal mounts
    // asynchronously inside it without changing the cached timeline count.
    await expect(pane.getByText("AI розпізнавання даних", { exact: true })).toBeAttached();
    await expect.poll(() => pane.evaluate((element) => element.scrollHeight)).toBeGreaterThan(initialHeight);
    if (manualHeader) {
      await expect.poll(() => pane.evaluate((element) => element.scrollTop)).toBe(0);
    } else {
      await expect(latest).toBeInViewport();
      await expect.poll(() => pane.evaluate((element) => element.scrollHeight - element.clientHeight - element.scrollTop)).toBeLessThan(4);
    }
    noSend(delayed);
    await delayed.assertClean(); await delayed.context.close();
  }
  checks.push("actual delayed customer-card/extraction-portal layout keeps latest-message intent pinned and preserves explicit header-top intent without timeline changes");

  for (const width of [375, 390, 1440]) {
    const f = await fixture({ width, height: 900 }, { fulfillment: true, theme: width === 390 ? "dark" : "light" });
    const data = f.state.fulfillment;
    data.state.linked = true;
    await f.page.goto(`${base}/direct?conversation=${a}&ttn_order_id=${data.orderId}&ttn_shipment_id=${data.shipmentId}`);
    await expect(f.page.getByRole("button", { name: "Вставити в чернетку", exact: true })).toBeVisible();
    await expect(f.reply()).toHaveValue("");
    await f.page.getByRole("button", { name: "Вставити в чернетку", exact: true }).click();
    await expect(f.reply()).toHaveValue(/20400000000000/);
    const box = await f.reply().boundingBox();
    expect(box.y + box.height).toBeLessThanOrEqual(900);
    await expect(f.page.getByRole("button", { name: "Підтвердити відправлення", exact: true })).toBeVisible();
    noSend(f);
    await f.page.screenshot({ path: path.join(output, `fulfillment-ttn-${width}.png`), fullPage: true });
    await f.page.getByRole("button", { name: "Клієнт і замовлення", exact: true }).click();
    const profile = f.page.locator("[data-direct-profile]");
    await expect(profile.getByRole("heading", { name: "Олена Тестова", exact: true })).toBeInViewport();
    await expect(profile).toContainText(/19[.]10[.]2099/);
    if (width < 1024) {
      const identity = await profile.locator("[data-direct-profile-username]").boundingBox();
      const update = await profile.getByRole("button", { name: "Оновити профіль", exact: true }).boundingBox();
      const name = await profile.getByRole("heading", { name: "Олена Тестова", exact: true }).boundingBox();
      expect(name.width).toBeGreaterThan(120);
      expect(update.y).toBeGreaterThanOrEqual(identity.y + identity.height);
    }
    await f.page.screenshot({ path: path.join(output, `fulfillment-profile-${width}.png`), fullPage: false });
    await f.assertClean(); await f.context.close();
  }
  checks.push("TTN insertion into empty drafts on 375/390/1440 (dark/light), neutral wording and composer bounds");

  for (const broken of ["invalidRelation", "failReads"]) {
    const f = await fixture({ width: 1280, height: 900 }, { fulfillment: true });
    const data = f.state.fulfillment;
    data.state.linked = true; data.state[broken] = true;
    await f.page.goto(`${base}/direct?conversation=${a}&ttn_order_id=${data.orderId}&ttn_shipment_id=${data.shipmentId}`);
    await expect(f.page.locator("[data-direct-ttn-draft]").getByRole("alert")).toBeVisible();
    await f.reply().fill("Залишити ручну чернетку");
    await expect(f.page.getByRole("button", { name: "Вставити в чернетку", exact: true })).toHaveCount(0);
    f.state.extraTimeline.push({ id: `synthetic-inbound-after-${broken}`, conversation_id: a, direction: "INBOUND", text: `Нове повідомлення після помилки ${broken}`, received_at: "2026-10-19T10:02:00Z", delivery_status: "RECEIVED" });
    await expect(f.page.getByText(`Нове повідомлення після помилки ${broken}`, { exact: true })).toBeInViewport({ timeout: 10000 });
    noSend(f); await f.assertClean(); await f.context.close();
  }
  const legacy = await fixture({ width: 1280, height: 900 }, { fulfillment: true, multiWorkspace: true });
  const data = legacy.state.fulfillment; data.state.linked = true;
  await legacy.page.goto(`${base}/shipments?order_id=${data.orderId}`);
  await expect(legacy.page.getByRole("link", { name: handoff, exact: true })).toBeVisible();
  expect(legacy.api.filter((key) => key === "POST /api/v1/shipments")).toEqual([]);
  await legacy.page.locator(".account-profile-trigger").click();
  await legacy.page.getByRole("button", { name: /Другий синтетичний магазин/ }).click();
  await expect(legacy.page.getByText("Не вдалося відкрити відправлення. Спробуйте ще раз.").first()).toBeVisible();
  await legacy.page.locator(".account-profile-trigger").click();
  await legacy.page.getByRole("button", { name: /^Синтетичний магазин/ }).click();
  await expect(legacy.page.getByRole("link", { name: handoff, exact: true })).toBeVisible();
  noSend(legacy); await legacy.assertClean(); await legacy.context.close();
  checks.push("TTN relation mismatch/404 fail closed without changing manual draft; legacy order deep link opens existing shipment after workspace reset without duplicate create");

  const late = await fixture({ width: 1280, height: 900 }, { fulfillment: true });
  await late.page.goto(`${base}/direct?conversation=${a}`); await late.reply().fill("Попередня редакція");
  late.state.holdSend = true;
  await late.page.getByRole("button", { name: "Підтвердити відправлення", exact: true }).click();
  await expect.poll(() => typeof late.state.releaseSend).toBe("function");
  await late.reply().fill("Нова редакція до переходу");
  await late.page.getByRole("button", { name: "Клієнт і замовлення", exact: true }).click();
  await late.page.getByRole("link", { name: "Оформити замовлення", exact: true }).click();
  await expect(late.page.getByRole("dialog")).toBeVisible();
  late.state.releaseSend();
  await late.page.keyboard.press("Escape");
  await expect(late.page.getByRole("dialog")).toHaveCount(0);
  await late.page.locator('a[href="/direct"]').first().click();
  await late.card(a).click(); await expect(late.reply()).toHaveValue("Нова редакція до переходу");
  await late.card(b).click(); await expect(late.reply()).toHaveValue("");
  await late.assertClean(); await late.context.close();
  checks.push("late COMPLETED across wizard remount keeps newer revision and conversation ownership");
}
