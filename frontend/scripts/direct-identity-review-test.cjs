/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require("fs");
const vm = require("vm");
const ts = require("typescript");
const React = require("react");
const assert = require("node:assert/strict");

let chosen = null, candidates = [], mutationOptions, queryOptions, linked = [], invalidated = [], refetched = 0;
let mutationError = false, pending = false;
const mocks = name => {
  if (name === "react") return { ...React, useState: () => [chosen, v => { chosen = v; }] };
  if (name === "@tanstack/react-query") return {
    useQuery: options => { queryOptions = options; return { data: candidates, isLoading: false, isError: false, refetch: () => { refetched++; } }; },
    useMutation: options => { mutationOptions = options; return { isPending: pending, isError: mutationError, mutate: id => options.mutationFn(id) }; },
    useQueryClient: () => ({ invalidateQueries: x => { invalidated.push(x.queryKey); } }),
  };
  if (name === "@/components/crm-workspace") return { Button: () => null };
  if (name === "@/hooks/use-auth") return { useAuth: () => ({ currentWorkspace: { workspace_id: "w1" } }) };
  if (name === "@/i18n/provider") return { useI18n: () => ({ t: key => key }) };
  if (name === "@/services/direct") return {
    fetchDirectIdentityCandidates: (...args) => args,
    linkDirectIdentityCandidate: (...args) => { linked.push(args); },
  };
  return require(name);
};
const source = fs.readFileSync("src/components/direct-identity-review.tsx", "utf8");
const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
const loaded = {}; vm.runInNewContext(code, { exports: loaded, require: mocks });
function flatten(node) {
  if (Array.isArray(node)) return node.flatMap(flatten);
  if (!node || typeof node !== "object") return [];
  return [node, ...flatten(node.props?.children)];
}
const render = (hasOrder = false) => flatten(loaded.DirectIdentityReview({ conversationId: "c1", hasOrder }));
const button = (nodes, key) => nodes.find(n => n.props?.children === key && typeof n.props.onClick === "function");
candidates = [{ id: "cust-a", name: "Synthetic A", instagram_username: "@sample", phone_last_four: "1234" }];
let nodes = render();
assert.equal(queryOptions.enabled, true);
assert.equal(JSON.stringify(queryOptions.queryFn()), JSON.stringify(["c1", "w1"]));
assert.equal(linked.length, 0, "identity must not link automatically");
assert(button(nodes, "direct.identityChoose"));
assert(!button(nodes, "direct.identityConfirm"));
button(nodes, "direct.identityChoose").props.onClick();
assert.equal(chosen, "cust-a");
assert.equal(linked.length, 0, "selecting a candidate must not link automatically");
nodes = render();
assert(button(nodes, "direct.identityConfirm"));
button(nodes, "direct.identityCancel").props.onClick();
assert.equal(chosen, null);
nodes = render();
button(nodes, "direct.identityChoose").props.onClick();
nodes = render();
button(nodes, "direct.identityConfirm").props.onClick();
assert.equal(JSON.stringify(linked), JSON.stringify([["c1", "cust-a", "w1"]]));
mutationOptions.onSuccess();
assert.equal(JSON.stringify(invalidated), JSON.stringify([["direct-conversations","w1"], ["direct-customer-automation","w1","c1"], ["customers","w1"]]));
mutationOptions.onError();
assert.equal(chosen, null);
assert.equal(refetched, 1);
nodes = render(true);
assert.equal(button(nodes, "direct.identityChoose").props.disabled, true);
chosen = "cust-a"; nodes = render(true);
assert.equal(button(nodes, "direct.identityConfirm").props.disabled, true);
pending = true; nodes = render();
assert.equal(button(nodes, "direct.identityConfirm").props.disabled, true);
console.log("PASS identity review: scoped candidates, explicit confirmation, cancel, invalidation and order/pending guards");
