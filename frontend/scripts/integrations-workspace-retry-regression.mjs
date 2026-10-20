import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import vm from "node:vm";
const require = createRequire(new URL("../package.json", import.meta.url));
const ts = require("typescript");
const source = readFileSync(new URL("../src/services/api.ts", import.meta.url), "utf8");
for (const endpoint of ["/integrations/meta-ads/sync", "/integrations/nova-poshta/test-connection"]) {
  let workspace = "workspace-a", releaseRefresh, fetchCount = 0;
  const calls = [], exports = {};
  vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText, {
    exports, Headers, FormData, AbortController, setTimeout, clearTimeout, Error,
    fetch: async (url, init) => { fetchCount++; calls.push(new Headers(init.headers).get("X-Workspace-ID")); return { status: 401 }; },
    require: name => name.includes("/workspace") ? { normalizeWorkspaceId: id => id } : {
      API_BASE_URL: "/api/v1", COOKIE_SESSION_AUTH_ENABLED: true, SecureSessionExpiredError: class extends Error {},
      authStorage: { getCurrentWorkspaceId: () => workspace, getAccessToken: () => "synthetic-access", getRefreshToken: () => null, setTokens: () => {} },
      refreshAccessToken: () => new Promise(resolve => { releaseRefresh = resolve; }),
    },
  });
  const pending = exports.authenticatedFetch(endpoint, { method: "POST", headers: { "X-Workspace-ID": workspace } });
  while (!releaseRefresh) await new Promise(resolve => setImmediate(resolve));
  workspace = "workspace-b"; releaseRefresh({});
  await assert.rejects(pending, error => error.status === 409 && error.detail.detail.code === "workspace_changed");
  assert.equal(fetchCount, 1, "no retry to the new tenant");
  assert.deepEqual(calls, ["workspace-a"]);
  await assert.rejects(exports.authenticatedFetch(endpoint, { method: "POST", headers: { "X-Workspace-ID": "workspace-a" } }), error => error.status === 409);
  assert.equal(fetchCount, 1, "stale explicit scope rejected before dispatch");
}
console.log("Integration workspace retry regression passed: Ads and NP401 refresh retries and stale dispatch never rebind to a new tenant.");
