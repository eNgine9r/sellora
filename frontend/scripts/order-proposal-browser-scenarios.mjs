import path from "node:path";

const extraVariantId = "15151515-1515-4515-8515-151515151515";
const campaignId = "12121212-1212-4212-8212-121212121212";
export async function runOrderProposalScenarios({ fixture, base, expect, a, b, workspaceId, output, checks }) {
  const empty = (id) => ({ conversation_id: id, analysis_id: null, analysis_created_at: null, analysis_context_message_id: null, analysis_state: "MISSING", catalog_truncated: false, context_truncated: false, lines: [] });
  const candidate = (ff, overrides = {}) => ({ product_id: ff.productId, variant_id: ff.variantId, product_name: "Синтетичний светр", sku: "SYN-M", color: null, size: "M", price: "100", available_quantity: 20, ...overrides });
  const inbound = (ff) => ({ id: "inbound-fixture", mention_text: "SYN-M", quantity: 1, source: "INBOUND_SKU", evidence: [{ message_id: "16161616-1616-4616-8616-161616161616", snippet: "Хочу SYN-M" }], requires_review: false, match_status: "MATCHED", matched_by: "VARIANT_SKU", reason: "UNIQUE_EXACT_MATCH", candidates_truncated: false, candidates: [candidate(ff)] });
  const openStep2 = async (f, viaDirect = false) => {
    const ff = f.state.fulfillment;
    if (viaDirect) {
      await f.page.goto(`${base}/direct?conversation=${a}`);
      await f.reply().fill("Ручна чернетка до товарів");
      await f.page.getByRole("button", { name: "Клієнт і замовлення", exact: true }).click();
      await f.page.getByRole("link", { name: "Оформити замовлення", exact: true }).click();
    } else await f.page.goto(`${base}/orders?create=1&customer_id=${ff.customerId}&direct_conversation_id=${a}`);
    const wizard = f.page.getByRole("dialog", { name: "Оформити замовлення з Direct", exact: true });
    await expect(wizard).toBeVisible();
    await wizard.getByLabel("Місто", { exact: true }).fill("Ки");
    await wizard.getByRole("button", { name: "Київ", exact: true }).click();
    await wizard.getByRole("button", { name: "Відділення №1", exact: true }).click();
    await wizard.getByRole("button", { name: "Продовжити", exact: true }).click();
    await expect(wizard.locator("[data-direct-order-products]")).toBeVisible();
    return wizard;
  };
  const noRecognitionWrite = (f) => expect(f.api.filter((key) => /\/(analyze|reply\/send|reply\/prepare)$/.test(key))).toEqual([]);

  for (const width of [375, 390, 1280, 1440]) {
    const f = await fixture({ width, height: 900 }, { fulfillment: true, advertising: true, theme: width === 390 ? "dark" : "light" });
    const ff = f.state.fulfillment;
    ff.state.proposal = { ...empty(a), lines: [inbound(ff)] };
    const wizard = await openStep2(f, true);
    const proposal = wizard.locator("[data-direct-order-products]");
    const row = proposal.locator("[data-proposal-line]").first();
    await expect(row.getByRole("combobox")).toHaveValue(ff.variantId);
    expect(ff.state.payloads).toHaveLength(0);
    noRecognitionWrite(f);
    for (const [quantity, message] of [["-1", "Кількість має бути цілим"], ["21", "недостатньо доступного"]]) {
      await row.getByLabel("Кількість", { exact: true }).fill(quantity);
      await proposal.getByRole("button", { name: "Додати вибрані товари", exact: true }).click();
      await expect(proposal.getByRole("alert")).toContainText(message);
      expect(ff.state.payloads).toHaveLength(0);
    }
    await row.getByLabel("Кількість", { exact: true }).fill("3");
    await proposal.getByRole("button", { name: "Додати вибрані товари", exact: true }).click();
    let item = wizard.locator("[data-order-item]");
    await expect(item).toHaveCount(1);
    await expect(item.getByRole("combobox")).toHaveValue(ff.variantId);
    await item.getByLabel("Собівартість", { exact: true }).fill("40");
    await item.getByLabel("Ціна за одиницю", { exact: true }).fill("110");
    await wizard.getByText("Додаткові деталі (необов’язково)", { exact: true }).click();
    await expect(wizard.getByRole("combobox", { name: /^Рекламна кампанія/ })).toBeVisible();
    await wizard.getByRole("combobox", { name: /^Рекламна кампанія/ }).selectOption(campaignId);
    const requests = ff.state.proposalRequests;
    ff.state.proposal.lines[0].candidates[0].price = "999";
    await proposal.getByRole("button", { name: "Оновити пропозицію", exact: true }).click();
    await expect.poll(() => ff.state.proposalRequests).toBeGreaterThan(requests);
    await expect(proposal.getByRole("button", { name: "Оновити пропозицію", exact: true })).toBeEnabled();
    await proposal.getByRole("button", { name: "Додати вибрані товари", exact: true }).click();
    await expect(item).toHaveCount(1);
    await expect(item.getByLabel("Ціна за одиницю", { exact: true })).toHaveValue("110");
    await expect(item.getByLabel("Собівартість", { exact: true })).toHaveValue("40");
    await expect(item.getByLabel("Кількість", { exact: true })).toHaveValue("3");
    await expect(wizard.getByRole("combobox", { name: /^Рекламна кампанія/ })).toHaveValue(campaignId);
    await f.assertClean();
    await f.page.screenshot({ path: path.join(output, `proposal-${width}.png`), fullPage: false });
    await wizard.getByRole("button", { name: "Продовжити", exact: true }).click();
    await expect(wizard.locator("[data-fulfillment-product-cost]")).toContainText(/120[,.]00/);
    await expect(wizard.locator("[data-fulfillment-profit]")).toContainText(/210[,.]00/);
    await wizard.getByRole("button", { name: "Створити замовлення і ТТН", exact: true }).click();
    if (width < 1024) {
      // Success selects the order, opening its foreground mobile drawer.
      // Close only that drawer through its real header action; Escape closes
      // both overlays and clicking through it would bypass the seller flow.
      const details = f.page.getByRole("dialog", { name: "SYN-1001", exact: true });
      await expect(details).toBeVisible();
      await details.locator("header").getByRole("button", { name: "Закрити", exact: true }).click();
      await expect(details).toHaveCount(0);
    }
    const handoff = wizard.getByRole("link", { name: "Підготувати повідомлення з ТТН", exact: true });
    await expect(handoff).toBeVisible();
    await expect(handoff).toHaveAttribute("href", `/direct?conversation=${a}&ttn_order_id=${ff.orderId}&ttn_shipment_id=${ff.shipmentId}`);
    await expect(wizard.getByRole("link", { name: "Відкрити відправлення", exact: true })).toHaveAttribute("href", `/shipments?shipment_id=${ff.shipmentId}`);
    expect(ff.state.payloads).toHaveLength(1);
    expect(ff.state.payloads[0]).toMatchObject({ campaign_id: campaignId, items: [{ product_variant_id: ff.variantId, quantity: 3, unit_price: 110, unit_cost: 40 }] });
    await handoff.click();
    await expect(f.reply()).toHaveValue("Ручна чернетка до товарів");
    await f.page.getByRole("button", { name: "Вставити в чернетку", exact: true }).click();
    await f.page.getByRole("button", { name: "Замінити чернетку", exact: true }).click();
    await expect(f.reply()).toHaveValue(/створено накладну.*20400000000000/);
    noRecognitionWrite(f);
    await f.assertClean(); await f.context.close();
  }
  checks.push("proposal375/390/1280/1440: Direct -> explicit SKU apply -> review/payload -> existing TTN draft; invalid quantity/stock, manual cost/price/campaign preserved on refresh and repeat Apply; no automatic recognition/send");

  const ambiguous = await fixture({ width: 1280, height: 900 }, { fulfillment: true });
  const af = ambiguous.state.fulfillment;
  const second = candidate(af, { variant_id: extraVariantId, sku: "SYN-L", size: "L", price: null, available_quantity: 4 });
  af.state.extraVariants = [{ id: extraVariantId, workspace_id: workspaceId, product_id: af.productId, sku: "SYN-L", price: null, is_active: true }];
  af.state.extraInventory = [{ id: "second-stock", product_variant_id: extraVariantId, stock_quantity: 4, reserved_quantity: 0 }];
  af.state.proposal = { ...empty(a), analysis_state: "STALE", lines: [{ ...inbound(af), id: "analysis-fixture", source: "ANALYSIS_CONTEXT", evidence: [], requires_review: true, match_status: "AMBIGUOUS", reason: "MULTIPLE_VARIANTS", candidates: [candidate(af), second] }] };
  const wizard = await openStep2(ambiguous);
  const proposal = wizard.locator("[data-direct-order-products]");
  await expect(proposal).toContainText("Після аналізу діалог змінився");
  await expect(proposal.getByRole("combobox")).toHaveValue("");
  await proposal.getByRole("combobox").selectOption(extraVariantId);
  await proposal.getByRole("button", { name: "Додати вибрані товари", exact: true }).click();
  await expect(proposal.getByRole("alert")).toContainText("Підтвердьте перевірку");
  await proposal.getByRole("checkbox").check();
  await proposal.getByRole("button", { name: "Додати вибрані товари", exact: true }).click();
  await expect(proposal.getByRole("alert")).toContainText("ціну продажу");
  await proposal.getByLabel("Ціна продажу (вкажіть вручну)", { exact: true }).fill("125");
  await proposal.getByLabel("Кількість", { exact: true }).fill("2");
  await proposal.getByRole("button", { name: "Додати вибрані товари", exact: true }).click();
  await expect(wizard.locator("[data-order-item]").getByLabel("Ціна за одиницю", { exact: true })).toHaveValue("125");
  await wizard.getByRole("button", { name: "Додати позицію", exact: true }).click();
  await wizard.locator("[data-order-item]").last().getByRole("combobox").selectOption(extraVariantId);
  await expect(wizard.locator("[data-order-item]").last().getByLabel("Ціна за одиницю", { exact: true })).toHaveValue("");
  await wizard.locator("[data-order-item]").last().getByRole("combobox").selectOption(af.variantId);
  await expect(wizard.locator("[data-order-item]")).toHaveCount(2);
  noRecognitionWrite(ambiguous); await ambiguous.assertClean(); await ambiguous.context.close();
  checks.push("ambiguous stale AI is unselected, requires explicit review and manual price for null catalog price; manual item fallback remains available");

  const reviewed = await fixture({ width: 1280, height: 900 }, { fulfillment: true, advertising: true });
  const rf = reviewed.state.fulfillment;
  rf.state.extraVariants = [{ id: extraVariantId, workspace_id: workspaceId, product_id: rf.productId, sku: "SYN-L", price: "200", is_active: true }];
  rf.state.extraInventory = [{ id: "review-stock", product_variant_id: extraVariantId, stock_quantity: 20, reserved_quantity: 0 }];
  rf.state.proposal = { ...empty(a), analysis_id: "17171717-1717-4717-8717-171717171717", analysis_state: "COMPLETED", lines: [
    inbound(rf),
    { ...inbound(rf), id: "analysis-same-id", mention_text: "Синтетичний светр L", source: "ANALYSIS_CONTEXT", evidence: [], requires_review: true, candidates: [candidate(rf, { variant_id: extraVariantId, sku: "SYN-L", price: "200" })] },
  ] };
  const rw = await openStep2(reviewed);
  const rp = rw.locator("[data-direct-order-products]");
  await rp.getByRole("button", { name: "Додати вибрані товари", exact: true }).click();
  const existing = rw.locator("[data-order-item]").first();
  await existing.getByLabel("Ціна за одиницю", { exact: true }).fill("177");
  await existing.getByLabel("Собівартість", { exact: true }).fill("40");
  await existing.getByLabel("Кількість", { exact: true }).fill("2");
  await rw.getByText("Додаткові деталі (необов’язково)", { exact: true }).click();
  await rw.getByRole("combobox", { name: /^Рекламна кампанія/ }).selectOption(campaignId);
  const pending = rp.locator('[data-proposal-line="analysis-same-id"]');
  await pending.getByRole("combobox").selectOption(extraVariantId);
  await pending.getByLabel("Кількість", { exact: true }).fill("3");
  await pending.getByRole("checkbox").check();
  await expect(pending.getByRole("checkbox")).toBeChecked();
  rf.state.proposal.analysis_state = "STALE";
  for (let refresh = 0; refresh < 2; refresh++) {
    // Second refresh intentionally returns an identical already-stale payload.
    // Stable IDs/structural sharing must not make prior acknowledgement reusable.
    const reads = rf.state.proposalRequests;
    await rp.getByRole("button", { name: "Оновити пропозицію", exact: true }).click();
    await expect.poll(() => rf.state.proposalRequests).toBeGreaterThan(reads);
    await expect(rp.getByRole("button", { name: "Додати вибрані товари", exact: true })).toBeEnabled();
    await expect(pending.getByRole("checkbox")).not.toBeChecked();
    await expect(pending.getByRole("combobox")).toHaveValue(extraVariantId);
    await expect(pending.getByLabel("Кількість", { exact: true })).toHaveValue("3");
    await rp.getByRole("button", { name: "Додати вибрані товари", exact: true }).click();
    await expect(rp.getByRole("alert")).toContainText("Підтвердьте перевірку");
    await expect(rw.locator("[data-order-item]")).toHaveCount(1);
    await expect(existing.getByLabel("Ціна за одиницю", { exact: true })).toHaveValue("177");
    await expect(existing.getByLabel("Собівартість", { exact: true })).toHaveValue("40");
    await expect(existing.getByLabel("Кількість", { exact: true })).toHaveValue("2");
    await expect(rw.getByRole("combobox", { name: /^Рекламна кампанія/ })).toHaveValue(campaignId);
    await pending.getByRole("checkbox").check();
  }
  await rp.getByRole("button", { name: "Додати вибрані товари", exact: true }).click();
  await expect(rw.locator("[data-order-item]")).toHaveCount(2);
  await expect(rw.locator("[data-order-item]").last().getByLabel("Кількість", { exact: true })).toHaveValue("3");
  noRecognitionWrite(reviewed); await reviewed.assertClean(); await reviewed.context.close();
  checks.push("AI review binds to each verified snapshot: COMPLETED -> same-ID STALE -> identical already-STALE refresh requires renewed review, preserving pending selection and applied price/cost/quantity/campaign edits");

  const drift = await fixture({ width: 1280, height: 900 }, { fulfillment: true });
  const df = drift.state.fulfillment;
  df.state.extraVariants = [{ id: extraVariantId, workspace_id: workspaceId, product_id: df.productId, sku: "SYN-L", price: "300", is_active: true }];
  df.state.extraInventory = [{ id: "drift-stock", product_variant_id: extraVariantId, stock_quantity: 20, reserved_quantity: 0 }];
  df.state.proposal = { ...empty(a), lines: [
    { ...inbound(df), candidates: [candidate(df, { price: "130" })] },
    { ...inbound(df), id: "inbound-null-price", mention_text: "SYN-L", candidates: [candidate(df, { variant_id: extraVariantId, sku: "SYN-L", price: null })] },
  ] };
  const dw = await openStep2(drift);
  const dp = dw.locator("[data-direct-order-products]");
  await dp.getByLabel("Ціна продажу (вкажіть вручну)", { exact: true }).fill("123");
  await dp.getByRole("button", { name: "Додати вибрані товари", exact: true }).click();
  const di = dw.locator("[data-order-item]");
  await expect(di).toHaveCount(2);
  await expect(di.nth(0).getByLabel("Ціна за одиницю", { exact: true })).toHaveValue("130");
  await expect(di.nth(1).getByLabel("Ціна за одиницю", { exact: true })).toHaveValue("123");
  await di.nth(0).getByLabel("Ціна за одиницю", { exact: true }).fill("177");
  await di.nth(0).getByLabel("Собівартість", { exact: true }).fill("40");
  df.state.proposal.lines[0].candidates[0].price = "90";
  df.state.proposal.lines[1].candidates[0].price = "200";
  const reads = df.state.proposalRequests;
  await dp.getByRole("button", { name: "Оновити пропозицію", exact: true }).click();
  await expect.poll(() => df.state.proposalRequests).toBeGreaterThan(reads);
  await expect(dp.getByRole("button", { name: "Додати вибрані товари", exact: true })).toBeEnabled();
  await dp.getByRole("button", { name: "Додати вибрані товари", exact: true }).click();
  await expect(di.nth(0).getByLabel("Ціна за одиницю", { exact: true })).toHaveValue("177");
  await expect(di.nth(1).getByLabel("Ціна за одиницю", { exact: true })).toHaveValue("123");
  await dw.getByRole("button", { name: "Продовжити", exact: true }).click();
  await dw.getByRole("button", { name: "Створити замовлення і ТТН", exact: true }).click();
  await expect(dw.getByRole("link", { name: "Підготувати повідомлення з ТТН", exact: true })).toBeVisible();
  expect(df.state.payloads[0].items).toEqual([
    { product_variant_id: df.variantId, quantity: 1, unit_price: 177, unit_cost: 40 },
    { product_variant_id: extraVariantId, quantity: 1, unit_price: 123, unit_cost: 0 },
  ]);
  noRecognitionWrite(drift); await drift.assertClean(); await drift.context.close();
  checks.push("fresh proposal price130 beats cached catalog100; explicit manual123 for proposal-null beats cached300; refresh/reapply preserves existing edited prices/cost and actual payload");

  const fallback = await fixture({ width: 390, height: 900 }, { fulfillment: true });
  const sf = fallback.state.fulfillment; sf.state.holdProposal = true;
  const fallbackWizard = await openStep2(fallback);
  const panel = fallbackWizard.locator("[data-direct-order-products]");
  await expect(panel.getByRole("status")).toContainText("Читаємо");
  await expect.poll(() => typeof sf.state.releaseProposal).toBe("function");
  sf.state.holdProposal = false; sf.state.releaseProposal();
  await expect(panel).toContainText("Товарів для пропозиції немає");
  for (const [state, label] of [["FAILED", "Останній аналіз не завершився успішно"], ["MALFORMED", "Останній аналіз не містить надійного списку"], ["PENDING", "Збережений аналіз ще не завершений"]]) {
    sf.state.proposal = { ...empty(a), analysis_state: state };
    await panel.getByRole("button", { name: "Оновити пропозицію", exact: true }).click();
    await expect(panel.getByRole("button", { name: "Оновити пропозицію", exact: true })).toBeEnabled();
    await expect(panel).toContainText(label);
    await expect(panel.getByRole("combobox")).toHaveCount(0);
  }
  sf.state.proposalError = true;
  await panel.getByRole("button", { name: "Оновити пропозицію", exact: true }).click();
  await expect(panel.getByRole("alert")).toContainText("Не вдалося прочитати");
  await fallbackWizard.locator("[data-order-item]").getByRole("combobox").selectOption(sf.variantId);
  noRecognitionWrite(fallback); await fallback.assertClean(); await fallback.context.close();
  checks.push("proposal loading/missing/failed/malformed/pending/error states keep manual selection available and do not invoke analysis");

  const late = await fixture({ width: 1280, height: 900 }, { fulfillment: true });
  const lf = late.state.fulfillment; lf.state.proposal = { ...empty(a), lines: [inbound(lf)] }; lf.state.holdProposal = true;
  await openStep2(late); await expect.poll(() => typeof lf.state.releaseProposal).toBe("function");
  await late.page.evaluate(({ customer, conversation }) => history.pushState({}, "", `/orders?create=1&customer_id=${customer}&direct_conversation_id=${conversation}`), { customer: lf.customerId, conversation: b });
  const newWizard = late.page.getByRole("dialog");
  await newWizard.getByLabel("Місто", { exact: true }).fill("Ки");
  await newWizard.getByRole("button", { name: "Київ", exact: true }).click();
  await newWizard.getByRole("button", { name: "Відділення №1", exact: true }).click();
  await newWizard.getByRole("button", { name: "Продовжити", exact: true }).click();
  await expect(newWizard.locator("[data-direct-order-products]")).toContainText("Товарів для пропозиції немає");
  const oldResponse = late.page.waitForResponse((response) => response.url().includes(`/conversations/${a}/order-proposal`) && response.status() === 200);
  lf.state.holdProposal = false; lf.state.releaseProposal();
  await oldResponse;
  await expect(newWizard.locator("[data-proposal-line]")).toHaveCount(0);
  await expect(newWizard.locator("[data-order-item]").getByRole("combobox")).toHaveValue("");
  noRecognitionWrite(late); await late.assertClean(); await late.context.close();
  checks.push("late proposal from prior conversation cannot select or apply products in the new wizard context");

  const failedAnalysis = await fixture({ width: 1440, height: 900 });
  failedAnalysis.state.analysisStatus = "FAILED_SAFE";
  await failedAnalysis.page.goto(`${base}/direct?conversation=${a}`);
  await failedAnalysis.page.getByRole("button", { name: "Проаналізувати діалог", exact: true }).first().click();
  await expect(failedAnalysis.page.getByText("Не вдалося проаналізувати діалог. Спробуйте ще раз.", { exact: true }).first()).toBeVisible();
  await failedAnalysis.assertClean(); await failedAnalysis.context.close();
  checks.push("explicit analysis HTTP200 FAILED_SAFE surfaces failure rather than successful proposal refresh");
}
