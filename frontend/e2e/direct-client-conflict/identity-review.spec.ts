import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import uk from "../../src/i18n/messages/uk.json";

type Case = {
  conversation_id: string;
  display_name: string;
  candidate_ids: string[];
  candidate_names: string[];
  foreign_customer_id: string;
  foreign_customer_name: string;
  foreign_conversation_id: string;
};
type Manifest = {
  version: number;
  workspace_id: string;
  foreign_workspace_id: string;
  login: { email: string; password: string };
  cases: Record<string, Case>;
};
type NavigationObservation = { elapsed_ms: number; kind: string; path: string; status?: number };
const navigationEvidence = new WeakMap<Page, NavigationObservation[]>();

function fixture() {
  const file = process.env.SELLORA_DIRECT_CONFLICT_MANIFEST;
  if (!file) throw new Error("Private synthetic fixture manifest is required");
  const manifest = JSON.parse(readFileSync(file, "utf8")) as Manifest;
  if (manifest.version !== 1) throw new Error("Unsupported synthetic fixture manifest");
  return { file, manifest };
}

function verifyCommittedState(caseName: string, expected: "unbound" | "confirmed") {
  const { file } = fixture();
  const result = spawnSync("python", ["scripts/direct_client_conflict_e2e.py", "verify",
    "--manifest", file, "--case", caseName, "--expected", expected], {
    cwd: path.resolve(__dirname, "../../../backend"), encoding: "utf8", timeout: 15_000,
  });
  expect(result.status, result.stderr || result.error?.message).toBe(0);
}

async function loginAndOpenConflict(page: Page, scenario: Case, manifest: Manifest) {
  await page.goto("/login");
  await page.locator('input[name="email"]').fill(manifest.login.email);
  await page.locator('input[name="password"]').fill(manifest.login.password);
  const loggedIn = page.waitForResponse(response => response.url().endsWith("/auth/session/login") && response.request().method() === "POST");
  await page.getByRole("button", { name: uk.auth.login, exact: true }).click();
  const loginResponse = await loggedIn;
  expect(loginResponse.status()).toBe(200);
  const accessToken = (await loginResponse.json() as { access_token: string }).access_token;
  await page.waitForURL("**/dashboard");
  await page.goto(`/direct?conversation=${scenario.conversation_id}`);
  await openCustomerPanel(page, scenario);
  const conflict = page.waitForResponse(response => response.url().endsWith(`/conversations/${scenario.conversation_id}/customer-automation/ensure`) && response.request().method() === "POST");
  await page.getByRole("button", { name: "Створити prospect", exact: true }).click();
  expect((await conflict).status()).toBe(409);
  const review = page.locator("[data-direct-identity-review]:visible");
  await expect(review).toBeVisible();
  await expect(review.getByRole("button", { name: uk.direct.identityChoose, exact: true })).toHaveCount(2);
  await expect(review).not.toContainText(scenario.foreign_customer_name);
  await expect(review.getByRole("button", { name: uk.direct.identityConfirm, exact: true })).toHaveCount(0);
  return { review, accessToken };
}

async function openCustomerPanel(page: Page, scenario: Case) {
  await expect(page.locator("[data-direct-mobile-thread]")).toContainText(scenario.display_name);
  const details = page.locator("[data-direct-mobile-details]");
  if (await details.isVisible() && await details.getAttribute("open") === null) await details.locator("summary").click();
  return page.locator("[data-direct-customer-automation]:visible");
}

async function browserApi(page: Page, token: string, workspaceId: string, apiPath: string, customerId?: string) {
  return page.evaluate(async ({ token, workspaceId, apiPath, customerId }) => {
    const response = await fetch(`/api/v1${apiPath}`, {
      method: customerId ? "POST" : "GET",
      headers: { Authorization: `Bearer ${token}`, "X-Workspace-ID": workspaceId, "Content-Type": "application/json" },
      ...(customerId ? { body: JSON.stringify({ customer_id: customerId }) } : {}),
    });
    return { status: response.status, body: await response.json() };
  }, { token, workspaceId, apiPath, customerId });
}

test.beforeEach(async ({ context, page }) => {
  const started = Date.now();
  const observations: NavigationObservation[] = [];
  navigationEvidence.set(page, observations);
  page.on("framenavigated", frame => {
    if (frame === page.mainFrame()) observations.push({ elapsed_ms: Date.now() - started, kind: "navigation", path: new URL(frame.url()).pathname });
  });
  page.on("response", response => {
    const url = new URL(response.url());
    if (url.pathname.startsWith("/api/v1/auth/")) observations.push({ elapsed_ms: Date.now() - started, kind: "auth-response", path: url.pathname, status: response.status() });
  });
  // Abort external network access only; no API response is mocked or fulfilled.
  await context.route("**/*", route => {
    const url = new URL(route.request().url());
    return url.origin === "http://127.0.0.1:3100" ? route.continue() : route.abort("blockedbyclient");
  });
});

test.afterEach(async ({ page }, info) => {
  // Paths, elapsed times and status codes only: no request/response bodies,
  // query strings, Authorization headers, cookies or generated credentials.
  const evidence = { project: info.project.name, final_path: new URL(page.url()).pathname,
    observations: navigationEvidence.get(page) ?? [] };
  await info.attach("auth-navigation", { body: Buffer.from(JSON.stringify(evidence, null, 2)), contentType: "application/json" });
  console.log("Direct E2E navigation evidence: " + JSON.stringify(evidence));
  navigationEvidence.delete(page);
});

test("explicit selection and confirmation persist the chosen customer", async ({ page }, info) => {
  const { manifest } = fixture();
  const caseName = `${info.project.name}-confirm`;
  const scenario = manifest.cases[caseName];
  const { review } = await loginAndOpenConflict(page, scenario, manifest);
  let linkRequests = 0;
  page.on("request", request => { if (request.method() === "POST" && request.url().endsWith("/customer-automation/link")) linkRequests++; });
  const selected = review.locator(":scope > div").filter({ hasText: scenario.candidate_names[1] });
  await selected.getByRole("button", { name: uk.direct.identityChoose, exact: true }).click();
  await expect(selected.getByRole("button", { name: uk.direct.identityConfirm, exact: true })).toBeEnabled();
  expect(linkRequests).toBe(0);
  verifyCommittedState(caseName, "unbound");
  await info.attach("explicit-customer-confirmation", { body: await page.screenshot(), contentType: "image/png" });
  const linked = page.waitForResponse(response => response.url().endsWith(`/conversations/${scenario.conversation_id}/customer-automation/link`));
  await selected.getByRole("button", { name: uk.direct.identityConfirm, exact: true }).click();
  const response = await linked;
  expect(response.status()).toBe(200);
  expect((await response.json()).customer.id).toBe(scenario.candidate_ids[1]);
  expect(linkRequests).toBe(1);
  await expect(page.locator("[data-direct-customer-automation]:visible")).toContainText(scenario.candidate_names[1]);
  await expect(review).toHaveCount(0);
  await page.reload();
  await expect(await openCustomerPanel(page, scenario)).toContainText(scenario.candidate_names[1]);
  verifyCommittedState(caseName, "confirmed");
});

test("cancel after selecting a candidate leaves persisted identities untouched", async ({ page }, info) => {
  const { manifest } = fixture();
  const caseName = `${info.project.name}-cancel`;
  const scenario = manifest.cases[caseName];
  const { review } = await loginAndOpenConflict(page, scenario, manifest);
  let linkRequests = 0;
  page.on("request", request => { if (request.method() === "POST" && request.url().endsWith("/customer-automation/link")) linkRequests++; });
  const selected = review.locator(":scope > div").filter({ hasText: scenario.candidate_names[1] });
  await selected.getByRole("button", { name: uk.direct.identityChoose, exact: true }).click();
  await expect(selected.getByRole("button", { name: uk.direct.identityConfirm, exact: true })).toBeVisible();
  verifyCommittedState(caseName, "unbound");
  await selected.getByRole("button", { name: uk.direct.identityCancel, exact: true }).click();
  await expect(review.getByRole("button", { name: uk.direct.identityConfirm, exact: true })).toHaveCount(0);
  await expect(review.getByRole("button", { name: uk.direct.identityChoose, exact: true })).toHaveCount(2);
  expect(linkRequests).toBe(0);
  await page.reload();
  await expect(await openCustomerPanel(page, scenario)).not.toContainText(scenario.candidate_names[1]);
  verifyCommittedState(caseName, "unbound");
});

test("foreign candidates, conversations and workspace headers are denied without mutations", async ({ page }, info) => {
  const { manifest } = fixture();
  const caseName = `${info.project.name}-denial`;
  const scenario = manifest.cases[caseName];
  const { accessToken } = await loginAndOpenConflict(page, scenario, manifest);
  const base = `/direct/conversations/${scenario.conversation_id}/customer-automation`;
  const foreign = `/direct/conversations/${scenario.foreign_conversation_id}/customer-automation`;
  const requests = [
    { workspace: manifest.workspace_id, path: `${base}/link`, customer: scenario.foreign_customer_id, status: 409 },
    { workspace: manifest.workspace_id, path: `${foreign}/link`, customer: scenario.candidate_ids[1], status: 404 },
    { workspace: manifest.foreign_workspace_id, path: `${base}/link`, customer: scenario.candidate_ids[1], status: 403 },
    { workspace: manifest.workspace_id, path: `${foreign}/candidates`, customer: undefined, status: 404 },
    { workspace: manifest.foreign_workspace_id, path: `${base}/candidates`, customer: undefined, status: 403 },
  ];
  for (const request of requests) {
    const response = await browserApi(page, accessToken, request.workspace, request.path, request.customer);
    expect(response.status).toBe(request.status);
    expect(JSON.stringify(response.body)).not.toContain(scenario.foreign_customer_id);
    expect(JSON.stringify(response.body)).not.toContain(scenario.foreign_customer_name);
  }
  verifyCommittedState(caseName, "unbound");
});
