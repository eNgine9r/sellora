import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const policyPath = path.join(root, "frontend/vercel.json");
const workflowPath = path.join(root, ".github/workflows/ci.yml");
assert(existsSync(policyPath), "Vercel branch policy must be in the frontend project root");
const policy = JSON.parse(readFileSync(policyPath, "utf8"));
const rules = policy.git?.deploymentEnabled;
assert.equal(policy.$schema, "https://openapi.vercel.sh/vercel.json");
assert(rules && typeof rules === "object" && !Array.isArray(rules), "Expected branch-specific Vercel Git policy");
assert.deepEqual(Object.keys(rules).sort(), ["**", "main", "qa/preview-ready"].sort(),
  "Do not enable another auto-preview branch without reviewing the deployment budget");
assert.equal(rules["**"], false, "Unknown branches must not trigger automatic preview");
assert.equal(rules.main, true, "Main must continue to deploy automatically to Sellora staging");
assert.equal(rules["qa/preview-ready"], true, "Only dedicated QA-ready branch may receive auto-preview");
assert.equal(policy.ignoreCommand, undefined, "Ignoring builds does not solve deployment creation quota");
assert.equal(policy.github?.enabled, undefined, "Do not use deprecated global Git integration switch");

// Mirrors the documented Vercel rule that any matching true overrides a matching false.
// Since our only wildcard is **, all other rules are exact branch names.
function shouldDeploy(branch) {
  const matching = Object.entries(rules).filter(([pattern]) => pattern === "**" || pattern === branch);
  return matching.length ? matching.some(([, enabled]) => enabled === true) : true;
}

for (const branch of ["main", "qa/preview-ready"]) {
  assert(shouldDeploy(branch), `Expected auto-deploy for ${branch}`);
}
for (const branch of [
  "ops/vercel-deployment-budget-302",
  "codex/2026-10-22-desktop-list-actions-standard",
  "fix/instagram-login",
  "feat/inventory-ux",
  "dependabot/npm_and_yarn/next-15",
  "qa/preview-ready-experiment",
  "random-branch",
]) {
  assert(!shouldDeploy(branch), `Unexpected auto-deploy for ${branch}`);
}

assert(existsSync(path.join(root, "frontend/package.json")), "Expected Vercel application in frontend/");
const ci = readFileSync(workflowPath, "utf8");
assert(ci.includes("  pull_request:") && ci.includes("  push:"),
  "GitHub CI must keep checking pull requests and main");
assert(ci.includes("branches: [main]"), "Main CI protection must remain intact");
console.log("Sellora deployment budget policy passed (main + dedicated QA auto-deploy only).");
