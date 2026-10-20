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
vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText, {
  exports, sessionStorage, Date, Map, Error, JSON,
  require: name => name.includes("auth.service") ? { authStorage: { getCurrentWorkspaceId: () => workspace, getCurrentActorId: () => actor } } : {
    fetchMetaAdsStatus: async () => { statusCount++; return { ...status, connected }; },
    metaAdsRequest: async () => { postCount++; await new Promise(resolve => { release = resolve; }); connected = true; return status; },
  },
});
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
