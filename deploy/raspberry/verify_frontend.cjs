// Browser canary against the public Vercel site, with no customer mutations.
const assert = require("node:assert/strict");
const { chromium } = require(process.env.PLAYWRIGHT_MODULE);

async function main() {
  const frontend = new URL(process.env.FRONTEND_URL);
  const api = new URL(process.env.TARGET_API_URL);
  assert.equal(frontend.protocol, "https:");
  assert.equal(api.protocol, "https:");
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    const serverErrors = [];
    const networkFailures = [];
    const pageErrors = [];
    page.on("pageerror", error => pageErrors.push(error.name));
    page.on("response", response => {
      const url = new URL(response.url());
      if (url.origin === api.origin && response.status() >= 500) serverErrors.push(response.status());
    });
    page.on("requestfailed", request => {
      if (new URL(request.url()).origin === api.origin) networkFailures.push(request.failure()?.errorText || "FAILED");
    });
    const initial = await page.goto(frontend.origin + "/login", { waitUntil: "domcontentloaded", timeout: 45000 });
    assert.equal(initial.status(), 200);
    await page.locator('input[type="email"]').fill(process.env.STAGING_OWNER_EMAIL);
    await page.locator('input[type="password"]').fill(process.env.STAGING_OWNER_PASSWORD);
    const loginResponse = page.waitForResponse(response =>
      response.url() === api.href.replace(/\/$/, "") + "/auth/login" &&
      response.request().method() === "POST", { timeout: 45000 });
    const currentUserResponse = page.waitForResponse(response =>
      response.url() === api.href.replace(/\/$/, "") + "/auth/me" &&
      response.status() === 200, { timeout: 45000 });
    await page.locator('button[type="submit"]').click();
    assert.equal((await loginResponse).status(), 200);
    assert.equal((await currentUserResponse).status(), 200);
    await page.waitForURL(url => url.pathname === "/dashboard", { timeout: 45000 });
    await page.locator("main").waitFor({ state: "visible", timeout: 20000 });
    await page.waitForLoadState("networkidle", { timeout: 20000 });
    assert.deepEqual(serverErrors, []);
    assert.deepEqual(networkFailures, []);
    assert.deepEqual(pageErrors, []);
    console.log(JSON.stringify({
      public_frontend: frontend.origin,
      public_api: api.href,
      browser: "Chromium",
      login_http: 200,
      current_user_http: 200,
      authenticated_dashboard_rendered: true,
      api_server_errors: serverErrors.length,
      api_network_failures: networkFailures.length,
      browser_page_errors: pageErrors.length,
      no_tailnet_client: true,
      screenshots_or_auth_state_saved: false
    }));
    await context.close();
  } finally {
    await browser.close();
  }
}
main().catch(error => {
  console.error("PUBLIC_BROWSER_CANARY_FAILED: " + error.name);
  process.exitCode = 1;
});
