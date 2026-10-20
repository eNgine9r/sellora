import path from "node:path";

export async function runAdvertisingScenarios({ fixture, base, expect, output, checks, workspaceId }) {
  for (const width of [375, 390, 1280, 1440]) {
    const f = await fixture({ width, height: 900 }, { advertising: true });
    const ads = f.state.advertising.state;
    ads.hold = true;
    await f.page.goto(`${base}/advertising`);
    const section = f.page.locator("[data-crm-attribution]");
    await expect(section.getByRole("status")).toHaveText("Завантажуємо продажі CRM…");
    await expect.poll(() => typeof ads.release).toBe("function");
    ads.hold = false; ads.release();
    await expect(section.getByRole("heading", { name: "Продажі CRM за кампаніями" })).toBeVisible();
    await expect(section.locator("[data-crm-coverage]")).toContainText(/80\s*%/);
    await expect(f.page.getByRole("heading", { name: "Внесені рекламні метрики", exact: true })).toBeVisible();
    const source = f.page.locator("[data-advertising-reporting-source]");
    await expect(source).toBeVisible();
    await expect(source).toContainText("Рекламні метрики внесені вручну або імпортовані");
    await expect(source).toContainText("ручна синхронізація Meta Ads");
    await expect(source).toContainText("доступність синхронізації дивіться в інтеграціях.");
    await expect(source).not.toContainText(/MVP|Manual\/import|campaign\/adset|NaN|Infinity/);
    await expect(f.page.locator("[data-advertising-methodology]")).not.toHaveAttribute("open", "");
    const visibleRows = section.locator(width < 1024 ? "[data-crm-mobile]" : "[data-crm-desktop]");
    await expect(visibleRows).toBeVisible();
    await expect(visibleRows).toContainText("Синтетична реклама");
    await expect(visibleRows).toContainText("Архівна");
    await expect(visibleRows).toContainText("Без визначеної кампанії");
    if (width === 375 || width === 1440) {
      await section.screenshot({ path: path.join(output, `advertising-report-${width}.png`) });
      if (width === 375) await visibleRows.getByRole("article").first().screenshot({ path: path.join(output, "advertising-campaign-card-375.png") });
    }
    await expect(section.getByRole("link", { name: "Вказати кампанію в замовленнях" })).toHaveAttribute("href", "/orders");
    await f.page.getByLabel("Початок періоду", { exact: true }).fill("2026-10-01");
    await expect(section.locator('time[datetime="2026-10-01"]')).toHaveText("01.10.2026");
    ads.release = null; ads.hold = true;
    await f.page.getByLabel("Кінець періоду", { exact: true }).fill("2026-10-02");
    await expect(section.getByRole("status")).toBeVisible();
    await expect(section.locator("[data-crm-totals]")).toHaveCount(0);
    await expect.poll(() => typeof ads.release).toBe("function");
    ads.hold = false; ads.release();
    await expect(section.locator('time[datetime="2026-10-01"]')).toHaveText("01.10.2026");
    await expect(section.locator('time[datetime="2026-10-02"]')).toHaveText("02.10.2026");
    await expect(section.locator("[data-crm-coverage]")).toContainText(/50\s*%/);
    await expect(section.locator("[data-crm-totals]")).toContainText("1,84");
    await expect(section.locator("[data-crm-totals]")).toContainText(/(?<![\d,])543,48\s*(?:грн|₴)/);
    await expect(section.locator("[data-crm-totals]")).toContainText(/(?<!\d)1\s+000,00\s*(?:грн|₴)/);
    await expect.poll(() => ads.requests.some((r) => r.key.endsWith("/crm-attribution") && r.start === "2026-10-01" && r.end === "2026-10-02" && r.workspace === workspaceId)).toBe(true);
    await f.page.screenshot({ path: path.join(output, `advertising-${width}.png`), fullPage: false });
    await f.assertClean();
    expect(f.api.filter((key) => !key.startsWith("GET "))).toEqual([]);
    await f.context.close();
    checks.push(`advertising ${width}: localized dates/currency/fractional ratio, current range, source separation, archived/unattributed, loading, responsive layout, no writes`);
  }
  const f = await fixture({ width: 390, height: 844 }, { advertising: true });
  const ads = f.state.advertising.state;
  ads.mode = "empty";
  await f.page.goto(`${base}/advertising`);
  const section = f.page.locator("[data-crm-attribution]");
  await expect(section.locator("[data-crm-empty]")).toContainText("У цьому періоді ще немає");
  await expect(section.locator("[data-crm-coverage]")).toContainText("—");
  ads.mode = "error";
  await f.page.getByLabel("Початок періоду", { exact: true }).fill("2026-10-01");
  await expect(section.getByRole("alert")).toContainText("Не вдалося завантажити продажі CRM", { timeout: 20000 });
  await expect(section.locator("[data-crm-totals]")).toHaveCount(0);
  ads.mode = "populated";
  await section.getByRole("button", { name: "Спробувати ще раз" }).click();
  await expect(section.locator("[data-crm-coverage]")).toContainText(/80\s*%/);
  const reads = ads.requests.filter((r) => r.key.endsWith("/crm-attribution")).length;
  await f.page.getByLabel("Початок періоду", { exact: true }).fill("2027-01-01");
  await expect(section.getByRole("alert")).toHaveText("Початок періоду має бути не пізніше кінця.");
  expect(ads.requests.filter((r) => r.key.endsWith("/crm-attribution")).length).toBe(reads);
  await f.assertClean(); await f.context.close();
  checks.push("advertising empty, error hides totals, retry recovery, invalid range without CRM query");
}
