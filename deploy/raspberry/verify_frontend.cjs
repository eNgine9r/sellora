// Browser canary against the public Vercel site, with no customer mutations.
const assert = require("node:assert/strict");
const { chromium } = require(process.env.PLAYWRIGHT_MODULE);

let step = "initialize";
let diagnostics = {};
async function main() {
  const frontend = new URL(process.env.FRONTEND_URL);
  const api = new URL(process.env.TARGET_API_URL);
  assert.equal(frontend.protocol, "https:");
  assert.equal(api.protocol, "https:");
  assert.equal(api.origin, frontend.origin, "Browser API must remain on the frontend origin");
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const directBackendRequests = [];
    await context.route("**/*", route => {
      const url = new URL(route.request().url());
      if (url.hostname.endsWith(".ts.net") || ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)) {
        directBackendRequests.push(url.hostname);
        return route.abort("blockedbyclient");
      }
      return route.continue();
    });
    const page = await context.newPage();
    const serverErrors = [];
    const networkFailures = [];
    const pageErrors = [];
    const authRequests = [];
    const authResponses = [];
    diagnostics = { serverErrors, networkFailures, pageErrors, authRequests, authResponses, directBackendRequests };
    page.on("request", request => { const u = new URL(request.url()); if (u.origin === api.origin && u.pathname.includes("auth")) authRequests.push({path:u.pathname,method:request.method()}); });
    page.on("pageerror", error => pageErrors.push(error.name));
    page.on("response", response => {
      const url = new URL(response.url());
      if (url.origin === api.origin && url.pathname.includes("auth")) authResponses.push({path:url.pathname,status:response.status()});
      if (url.origin === api.origin && response.status() >= 500) serverErrors.push(response.status());
    });
    page.on("requestfailed", request => {
      if (new URL(request.url()).origin === api.origin) networkFailures.push(request.failure()?.errorText || "FAILED");
    });
    step = "load_login";
    const initial = await page.goto(frontend.origin + "/login", { waitUntil: "domcontentloaded", timeout: 45000 });
    assert.equal(initial.status(), 200);
    await page.waitForLoadState("networkidle", { timeout: 20000 });
    step = "fill_credentials";
    await page.locator('input[type="email"]').fill(process.env.STAGING_OWNER_EMAIL);
    await page.locator('input[type="password"]').fill(process.env.STAGING_OWNER_PASSWORD);
    const loginResponse = page.waitForResponse(response =>
      response.url() === api.href.replace(/\/$/, "") + "/auth/login" &&
      response.request().method() === "POST", { timeout: 45000 });
    const currentUserResponse = page.waitForResponse(response =>
      response.url() === api.href.replace(/\/$/, "") + "/auth/me" &&
      response.status() === 200, { timeout: 45000 });
    const authResponsesReady = Promise.all([loginResponse, currentUserResponse]);
    authResponsesReady.catch(() => {});
    step = "submit_login";
    await page.locator('button[type="submit"]').click();
    step = "await_api_login_and_current_user";
    const [loginResult, currentUserResult] = await authResponsesReady;
    assert.equal(loginResult.status(), 200);
    assert.equal(currentUserResult.status(), 200);
    step = "authenticated_dashboard";
    await page.waitForURL(url => url.pathname === "/dashboard", { timeout: 45000 });
    await page.locator("main").waitFor({ state: "visible", timeout: 20000 });
    await page.waitForLoadState("networkidle", { timeout: 20000 });
    assert.deepEqual(serverErrors, []);
    assert.deepEqual(networkFailures, []);
    assert.deepEqual(pageErrors, []);
    assert.deepEqual(directBackendRequests, [], "No browser access to tailnet or local API hosts");
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
      same_origin_api: true,
      direct_backend_browser_requests: directBackendRequests.length,
      screenshots_or_auth_state_saved: false
    }));
    await context.close();
  } finally {
    await browser.close();
  }
}
main().catch(error => {
  console.error(JSON.stringify({error:"PUBLIC_BROWSER_CANARY_FAILED",error_type:error.name,step,diagnostics}));
  process.exitCode = 1;
});
