import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import vm from "node:vm";
const require = createRequire(new URL("../package.json", import.meta.url));
const ts = require("typescript");
const storage = new Map();
const sessionStorage = { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) };
let workspace = "workspace-a", actor = "actor-a", connected = false, postCount = 0, statusCount = 0, release;
const status = { connected: true, connection_status: "CONNECTED" };
const source = readFileSync(new URL("../src/features/integrations/lib/meta-ads-intent.ts", import.meta.url), "utf8");
const exports = {};
const intentContext = {
  exports, sessionStorage, Date, Map, Error, JSON,
  require: name => name.includes("auth.service") ? { authStorage: { getCurrentWorkspaceId: () => workspace, getCurrentActorId: () => actor } } : {
    fetchMetaAdsStatus: async () => { statusCount++; return { ...status, connected }; },
    metaAdsRequest: async () => { postCount++; await new Promise(resolve => { release = resolve; }); connected = true; return status; },
  },
};
vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText, intentContext);
const intent = { workspace, actor, state: "synthetic-state", expires: "2099-01-01", phase: "pending" };
exports.saveAdsIntent(intent);
const first = exports.completeAdsIntent(intent, "synthetic-code", intent.state);
const second = exports.completeAdsIntent(exports.readAdsIntent(), "synthetic-code", intent.state);
assert.equal(first, second, "StrictMode repeat shares one exchange");
assert.equal(postCount, 1);
assert.ok(![...storage.values()].join("").includes("synthetic-code"), "code is never persisted");
release(); await first; await Promise.resolve();
assert.equal(exports.readAdsIntent().phase, "complete");
await exports.completeAdsIntent(exports.readAdsIntent(), null, null);
assert.equal(postCount, 1); assert.equal(statusCount, 1);
workspace = "workspace-b";
assert.equal(exports.matchesAdsIntent(intent, actor, workspace), false);
workspace = intent.workspace; actor = "actor-b";
assert.equal(exports.matchesAdsIntent(intent, actor, workspace), false);
connected = false;
await assert.rejects(exports.completeAdsIntent({ ...intent, state: "another-state", phase: "processing" }, null, null), /invalid_state/);
assert.equal(postCount, 1);
workspace = intent.workspace; actor = intent.actor;
const older = { ...intent, state: "older-state", phase: "pending" };
exports.saveAdsIntent(older);
const late = exports.completeAdsIntent(older, "synthetic-code", older.state);
const newer = { ...intent, state: "newer-state", phase: "pending" };
exports.saveAdsIntent(newer);
release(); await late;
assert.equal(exports.readAdsIntent().state, newer.state, "late old completion cannot overwrite newer reconnect");
exports.clearAdsIntent(older.state);
assert.equal(exports.readAdsIntent().state, newer.state, "stale handler cannot clear newer reconnect");
console.log("Meta Ads intent regression passed: StrictMode dedup, replay status recovery, disconnected recovery rejection, actor/workspace binding, code privacy.");

const window = { location: { search: "" }, history: { state: {}, replaceState() {} } };
// The intent module resolves the same memory-only callback capture as the page.
intentContext.window = window;
let hooks;
const pageExports = {};
const pageSource = readFileSync(new URL("../src/app/settings/integrations/meta-ads/callback/page.tsx", import.meta.url), "utf8");
const jsx = (type, props) => ({ type, props });
const react = {
  useRef: value => ({ current: value }),
  useState: value => {
    const target = hooks.states, index = target.length;
    target.push(value);
    return [value, next => { target[index] = next; }];
  },
  useEffect: effect => hooks.effects.push(effect),
};
vm.runInNewContext(ts.transpileModule(pageSource, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } }).outputText, {
  exports: pageExports, window,
  require: name => name === "react" ? react : name === "react/jsx-runtime" ? { jsx, jsxs: jsx } :
    name === "next/link" ? { default: "link" } :
    name.includes("crm-workspace") ? { WorkspaceHeader: "header", WorkspacePage: "main" } :
    name.includes("use-auth") ? { useAuth: () => ({ status: "authenticated", currentUser: { id: actor }, currentWorkspaceId: workspace, currentWorkspace: { role: "OWNER" } }) } :
    name.includes("i18n") ? { useI18n: () => ({ t: key => key }) } : exports,
});
function mountCallback(capture) {
  window.__selloraMetaAdsCallback = capture;
  hooks = { states: [], effects: [] };
  pageExports.default();
  const mounted = hooks;
  mounted.cleanup = mounted.effects[0]();
  return mounted;
}
const flush = () => new Promise(resolve => setImmediate(resolve));
const pendingB = { ...intent, state: "pending-B", phase: "pending" };
exports.saveAdsIntent(pendingB);
const beforeArrival = postCount;
const incomingA = mountCallback({ code: "synthetic-code-A", state: "stale-A", denied: false });
await flush();
assert.equal(incomingA.states[0], "invalid_state");
assert.equal(exports.readAdsIntent()?.state, pendingB.state, "actual page must preserve B when older A arrives");
assert.equal(exports.readAdsIntent()?.phase, "pending");
assert.equal(postCount, beforeArrival);
for (const code of ["synthetic-code-A", null]) {
  const missing = mountCallback({ code, state: null, denied: false });
  await flush();
  assert.equal(missing.states[0], "invalid_state");
  assert.equal(exports.readAdsIntent()?.state, pendingB.state, "missing incoming state must preserve pending B");
  assert.equal(postCount, beforeArrival);
}
const unassociatedDenial = mountCallback({ code: null, state: null, denied: true });
await flush();
assert.equal(unassociatedDenial.states[0], "denied");
assert.equal(exports.readAdsIntent()?.state, pendingB.state, "state-free denial cannot identify or clear pending B");
const firstB = mountCallback({ code: "synthetic-code-B", state: pendingB.state, denied: false });
assert.equal(postCount, beforeArrival + 1);
firstB.cleanup();
const secondB = mountCallback({ code: "synthetic-code-B", state: pendingB.state, denied: false });
const staleDuringB = mountCallback({ code: "synthetic-code-A", state: "stale-A", denied: false });
await flush();
assert.equal(staleDuringB.states[0], "invalid_state");
assert.equal(exports.readAdsIntent()?.state, pendingB.state);
assert.equal(postCount, beforeArrival + 1);
release(); await flush();
assert.equal(secondB.states[0], "success");
assert.equal(exports.readAdsIntent()?.phase, "complete");
assert.equal(postCount, beforeArrival + 1, "B completes exactly once after rejected A and missing-state arrivals");
const recoveredB = mountCallback({ code: null, state: null, denied: false });
await flush();
assert.equal(recoveredB.states[0], "success");
assert.equal(postCount, beforeArrival + 1);
const expiredOwn = { ...intent, state: "expired-own", phase: "pending", expires: "2000-01-01" };
exports.saveAdsIntent(expiredOwn);
const expiredPage = mountCallback({ code: "synthetic-expired-code", state: expiredOwn.state, denied: false });
await flush();
assert.equal(expiredPage.states[0], "invalid_state");
assert.equal(exports.readAdsIntent(), null, "matching expired attempt is cleared");
exports.saveAdsIntent({ ...pendingB, state: "denied-own" });
const deniedOwn = mountCallback({ code: null, state: "denied-own", denied: true });
await flush();
assert.equal(deniedOwn.states[0], "denied");
assert.equal(exports.readAdsIntent(), null, "matching denied attempt is cleared");
assert.equal(postCount, beforeArrival + 1);
console.log("Actual callback component + intent regression passed: stale/missing-state arrival preserves B; B completes once; in-flight stale arrival rejected; sanitized recovery succeeds.");
