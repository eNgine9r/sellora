/* eslint-disable @typescript-eslint/no-require-imports */
// Actual store/service in a VM, synthetic transport only; no browser/API bypass.
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const ts = require("typescript");

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
const tick = () => new Promise(resolve => setImmediate(resolve));
const actor = id => ({ id, first_name: "Synthetic", memberships: [{ workspace_id: `workspace-${id}` }] });
const tokens = id => ({ access_token: `access-${id}`, refresh_token: `refresh-${id}`, token_type: "bearer" });

function harness({ cookie = true, initial = null } = {}) {
  const requests = [], effects = [], state = [], timers = new Map(), changes = [];
  const local = new Map(), session = new Map();
  let timerId = 0, stateIndex = 0, cookieActor = initial, clears = 0;
  const storage = map => ({ getItem: key => map.get(key) ?? null, setItem: (key, value) => map.set(key, value), removeItem: key => map.delete(key) });
  const react = {
    createContext: () => ({ Provider: "Provider" }), useContext: () => null,
    useRef: value => ({ current: value }), useCallback: fn => fn, useMemo: fn => fn(),
    useEffect: fn => effects.push(fn),
    useState: initialValue => {
      const index = stateIndex++; state[index] = initialValue;
      return [initialValue, value => { state[index] = typeof value === "function" ? value(state[index]) : value; changes.push(index); }];
    },
  };
  function fetch(input, init) {
    const pending = deferred();
    const request = { path: new URL(input, "https://synthetic.invalid").pathname, init, pending, cookieAtSend: cookieActor };
    requests.push(request);
    init.signal.addEventListener("abort", () => {
      const error = new Error("Synthetic abort"); error.name = "AbortError";
      pending.reject(error);
      if (request.bodyPending && request.responded) request.bodyPending.reject(error);
    }, { once: true });
    request.respond = (status, data, { actor: nextActor, holdBody = false } = {}) => {
      request.responded = true;
      if (nextActor !== undefined) cookieActor = nextActor;
      if (holdBody) request.bodyPending = deferred();
      pending.resolve({ status, ok: status >= 200 && status < 300, headers: { get: () => null },
        json: () => request.bodyPending ? request.bodyPending.promise : Promise.resolve(data) });
    };
    return pending.promise;
  }
  const shared = {
    process: { env: { NODE_ENV: "production", NEXT_PUBLIC_COOKIE_SESSION_AUTH_ENABLED: String(cookie), NEXT_PUBLIC_API_BASE_URL: "/api/v1" } },
    window: { location: { hostname: "synthetic.invalid" }, localStorage: storage(local), sessionStorage: storage(session) },
    AbortController, URL, fetch,
    setTimeout: (fn, delay) => { const id = ++timerId; timers.set(id, { fn, delay }); return id; },
    clearTimeout: id => timers.delete(id),
  };
  function load(file, imports) {
    const code = ts.transpileModule(fs.readFileSync(file, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
    }).outputText;
    const exported = {};
    vm.runInNewContext(code, { ...shared, exports: exported, require: name => {
      if (name in imports) return imports[name];
      throw new Error(`Unexpected VM import: ${name}`);
    } });
    return exported;
  }
  const workspace = { normalizeWorkspaceId: value => value || null };
  const service = load("src/services/auth.service.ts", { "@/lib/workspace": workspace });
  if (initial) {
    service.authStorage.setTokens(tokens(initial));
    service.authStorage.setCurrentUser(actor(initial));
    service.authStorage.setCurrentWorkspaceId(`workspace-${initial}`);
  }
  const originalClear = service.authStorage.clear.bind(service.authStorage);
  service.authStorage.clear = () => { clears++; originalClear(); };
  const store = load("src/stores/auth.store.tsx", {
    react, "react/jsx-runtime": { jsx: (type, props) => ({ type, props }) },
    "@tanstack/react-query": { useQueryClient: () => ({ clear() {}, cancelQueries() {} }) },
    "@/lib/workspace": workspace, "@/services/auth.service": service,
  });
  const context = store.AuthProvider({ children: null }).props.value;
  return {
    requests, timers, service, context, changes, mount: () => effects[0](),
    snapshot: () => ({ status: state[0], user: state[1]?.id ?? null, workspace: state[2], error: state[3],
      token: service.authStorage.getAccessToken(), cookie: cookieActor, clears }),
    request: suffix => requests.find(request => request.path.endsWith(suffix) && !request.responded),
    expire: delay => { const match = [...timers].find(([, entry]) => entry.delay === delay); assert(match, "Expected bounded request timer"); timers.delete(match[0]); match[1].fn(); },
  };
}

async function completeLogin(target, id = "new") {
  await tick();
  const request = target.request("/login"); assert(request, "Expected real login request");
  const prior = new Set(target.requests);
  request.respond(200, tokens(id), { actor: id });
  await tick();
  const me = target.requests.find(item => item.path.endsWith("/me") && !item.responded && !prior.has(item));
  assert(me, "Expected current-user request");
  me.respond(200, actor(id));
  await tick();
}
function assertActor(target, id) {
  const state = target.snapshot();
  assert.equal(state.status, "authenticated"); assert.equal(state.user, id);
  assert.equal(state.workspace, `workspace-${id}`); assert.equal(state.token, `access-${id}`);
}

const cases = [];
const test = (name, run) => cases.push({ name, run });

for (const outcome of ["failure", "success"]) test(`original stale bootstrap ${outcome} reproduction`, async () => {
  const target = harness(); target.mount(); await tick();
  const bootstrap = target.request("/refresh");
  const login = target.context.login("synthetic@example.invalid", "synthetic-password");
  await tick();
  // Preserve the original ordering where the unfixed store permits it. The
  // fixed store instead drains bootstrap before sending the explicit login.
  const alreadySent = Boolean(target.request("/login"));
  if (alreadySent) await completeLogin(target);
  bootstrap.respond(outcome === "failure" ? 401 : 200, tokens("old"), { actor: outcome === "failure" ? null : "old" });
  await tick();
  const staleMe = target.request("/me");
  if (staleMe) { staleMe.respond(200, actor("old")); await tick(); }
  if (!alreadySent) await completeLogin(target);
  await login; await tick();
  assertActor(target, "new");
  assert.equal(target.snapshot().cookie, "new", "Late old Set-Cookie must not replace explicit login");
  assert.equal(target.snapshot().clears, 0, "Superseded bootstrap must not clear auth/cache");
});

test("cookie login drains bootstrap before any explicit request or stale state write", async () => {
  const target = harness(); target.mount(); await tick();
  const login = target.context.login("synthetic@example.invalid", "synthetic-password"); await tick();
  assert.deepEqual(target.requests.map(item => item.path), ["/api/v1/auth/session/refresh"]);
  target.request("/refresh").respond(200, tokens("old"), { actor: "old" }); await tick();
  assert.equal(target.snapshot().token, null); assert.equal(target.snapshot().user, null);
  assert.equal(target.request("/login").cookieAtSend, "old");
  await completeLogin(target); await login; assertActor(target, "new");
});

test("all initial attempts drain, including a StrictMode replay", async () => {
  const target = harness({ initial: "old" }); target.mount(); target.mount(); await tick();
  const [first, second] = target.requests;
  first.respond(401); await tick(); // First attempt has already begun cookie refresh.
  const login = target.context.login("synthetic@example.invalid", "synthetic-password");
  second.respond(200, actor("old")); await tick();
  assert.equal(Boolean(target.request("/login")), false, "Last bootstrap completing must not hide an earlier refresh");
  target.request("/refresh").respond(200, tokens("old"), { actor: "old" }); await tick();
  await completeLogin(target); await login; assertActor(target, "new");
});

test("late failed access-token bootstrap cannot start a refresh after login intent", async () => {
  const target = harness({ initial: "old" }); target.mount(); await tick();
  const login = target.context.login("synthetic@example.invalid", "synthetic-password");
  target.request("/me").respond(401); await tick();
  assert.equal(Boolean(target.request("/refresh")), false);
  await completeLogin(target); await login; assertActor(target, "new");
});

test("logout drains earlier Set-Cookie and cannot resurrect its actor", async () => {
  const target = harness(); target.mount(); await tick();
  const logout = target.context.logout(); await tick();
  assert.equal(Boolean(target.request("/logout")), false);
  target.request("/refresh").respond(200, tokens("old"), { actor: "old" }); await tick();
  assert.equal(target.snapshot().user, null);
  assert.equal(target.request("/logout").cookieAtSend, "old");
  target.request("/logout").respond(200, null, { actor: null }); await logout;
  const state = target.snapshot();
  assert.equal(state.status, "unauthenticated"); assert.equal(state.token, null);
  assert.equal(state.workspace, null); assert.equal(state.cookie, null); assert.equal(state.clears, 1);
});

test("normal cookie bootstrap/login and failed then confirmed logout retain contracts", async () => {
  const target = harness(); target.mount(); await tick();
  target.request("/refresh").respond(200, tokens("old"), { actor: "old" }); await tick();
  target.request("/me").respond(200, actor("old")); await tick(); assertActor(target, "old");
  const login = target.context.login("synthetic@example.invalid", "synthetic-password"); await completeLogin(target); await login;
  const logout = target.context.logout(); await tick();
  assertActor(target, "new"); // No local logout before server confirmation.
  target.request("/logout").respond(503); await assert.rejects(logout, /Unable to revoke secure session/);
  assertActor(target, "new"); assert.equal(target.snapshot().clears, 0);
  const retry = target.context.logout(); await tick();
  target.request("/logout").respond(200, null, { actor: null }); await retry;
  assert.equal(target.snapshot().status, "unauthenticated"); assert.equal(target.snapshot().token, null);
});

test("late explicit login user read cannot resurrect a completed logout", async () => {
  const target = harness();
  const login = target.context.login("synthetic@example.invalid", "synthetic-password"); await tick();
  target.request("/login").respond(200, tokens("old"), { actor: "old" }); await tick();
  const me = target.request("/me");
  const logout = target.context.logout(); await tick();
  target.request("/logout").respond(200, null, { actor: null }); await logout;
  me.respond(200, actor("old")); await login;
  assert.equal(target.snapshot().status, "unauthenticated"); assert.equal(target.snapshot().token, null);
});

for (const outcome of [200, 401]) test(`legacy cached bootstrap ${outcome} cannot overwrite newer login`, async () => {
  const target = harness({ cookie: false, initial: "old" }); target.mount(); await tick();
  const bootstrap = target.request("/me");
  const login = target.context.login("synthetic@example.invalid", "synthetic-password"); await completeLogin(target); await login;
  bootstrap.respond(outcome, actor("old")); await tick();
  assertActor(target, "new"); assert.equal(Boolean(target.request("/refresh")), false);
  const logout = target.context.logout(); await logout;
  assert.equal(Boolean(target.request("/logout")), false, "Legacy logout remains local");
  assert.equal(target.snapshot().status, "unauthenticated");
});

for (const stage of ["refresh body", "current-user body"]) test(`${stage} deadline bounds bootstrap drain without sleeps`, async () => {
  const target = harness({ initial: stage === "current-user body" ? "old" : null }); target.mount(); await tick();
  const pending = target.requests[0];
  pending.respond(200, null, { actor: "old", holdBody: true }); await tick();
  const login = target.context.login("synthetic@example.invalid", "synthetic-password"); await tick();
  assert.equal(Boolean(target.request("/login")), false);
  target.expire(12_000); await tick();
  await completeLogin(target); await login; assertActor(target, "new");
});

for (const kind of ["refresh", "me"]) test(`${kind} body timeout retains AuthNetworkError contract`, async () => {
  const target = harness();
  const pending = kind === "refresh" ? target.service.refreshCookieSession() : target.service.fetchCurrentUser("synthetic-access"); await tick();
  target.request("/" + kind).respond(200, null, { holdBody: true }); await tick();
  const rejected = assert.rejects(pending, error => error.name === "AuthNetworkError");
  target.expire(12_000); await rejected;
});

test("a passive effect after explicit login intent cannot start bootstrap", async () => {
  const target = harness();
  const login = target.context.login("synthetic@example.invalid", "synthetic-password");
  target.mount(); await tick();
  assert.equal(Boolean(target.request("/refresh")), false);
  await completeLogin(target); await login; assertActor(target, "new");
});

test("normal anonymous legacy login/logout retain their endpoints", async () => {
  const target = harness({ cookie: false }); target.mount(); await tick();
  assert.equal(target.snapshot().status, "unauthenticated");
  const login = target.context.login("synthetic@example.invalid", "synthetic-password"); await completeLogin(target); await login;
  assertActor(target, "new");
  assert.equal(target.requests[0].path, "/api/v1/auth/login");
  await target.context.logout(); assert.equal(target.snapshot().status, "unauthenticated");
  assert.equal(target.requests.length, 2);
});

test("cookie refresh keeps the single 409 retry and expired-session error contract", async () => {
  const target = harness();
  const refresh = target.service.refreshCookieSession(); await tick();
  target.request("/refresh").respond(409); await tick(); target.expire(350); await tick();
  const rejected = assert.rejects(refresh, error => error.name === "SecureSessionExpiredError");
  target.request("/refresh").respond(401); await rejected;
  assert.equal(target.requests.length, 2);
});

test("normal anonymous bootstrap fails closed and invalid credentials remain distinct", async () => {
  const target = harness(); target.mount(); await tick();
  target.request("/refresh").respond(401); await tick();
  assert.equal(target.snapshot().status, "unauthenticated"); assert.equal(target.snapshot().clears, 1);
  const login = target.context.login("synthetic@example.invalid", "synthetic-password"); await tick();
  const rejected = assert.rejects(login, error => error.name === "InvalidCredentialsError");
  target.request("/login").respond(401); await rejected;
  assert.equal(target.snapshot().status, "unauthenticated");
});

for (const failure of ["credentials", "current user"]) test(`pending bootstrap followed by failed ${failure} settles loading`, async () => {
  const target = harness(); target.mount(); await tick();
  const login = target.context.login("synthetic@example.invalid", "synthetic-password");
  const rejected = assert.rejects(login, error => failure === "credentials"
    ? error.name === "InvalidCredentialsError" : error.message === "Unable to load current user");
  target.request("/refresh").respond(401); await tick();
  const request = target.request("/login");
  if (failure === "credentials") request.respond(401);
  else {
    request.respond(200, tokens("new"), { actor: "new" }); await tick();
    target.request("/me").respond(503);
  }
  await rejected;
  assert.equal(target.snapshot().status, "unauthenticated");
  assert.equal(target.snapshot().user, null); assert.equal(target.snapshot().workspace, null);
  assert.equal(target.snapshot().token, null, "Unverified login must not replace client credentials");
});

for (const failure of ["credentials", "current user"]) test(`failed ${failure} preserves prior authenticated client state`, async () => {
  const target = harness({ initial: "old" }); target.mount(); await tick();
  target.request("/me").respond(200, actor("old")); await tick(); assertActor(target, "old");
  const login = target.context.login("synthetic@example.invalid", "synthetic-password"); await tick();
  const rejected = assert.rejects(login, error => failure === "credentials"
    ? error.name === "InvalidCredentialsError" : error.message === "Unable to load current user");
  if (failure === "credentials") target.request("/login").respond(401);
  else {
    target.request("/login").respond(200, tokens("new"), { actor: "new" }); await tick();
    target.request("/me").respond(503);
  }
  await rejected; assertActor(target, "old"); assert.equal(target.snapshot().clears, 0);
});

(async () => {
  const watchdog = setTimeout(() => { console.error("Auth bootstrap profile stalled on an unresolved promise"); process.exitCode = 1; }, 5_000);
  let failed = 0;
  for (const { name, run } of cases) {
    try { await run(); console.log(`PASS ${name}`); }
    catch (error) { failed++; console.error(`FAIL ${name}: ${error.message}`); }
  }
  console.log(`Auth bootstrap profile: ${cases.length - failed}/${cases.length} passed`);
  clearTimeout(watchdog);
  if (failed) process.exitCode = 1;
})();
