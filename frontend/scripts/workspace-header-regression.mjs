import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const UUID_PATTERN = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;

function normalizeWorkspaceId(value) {
  if (typeof value !== "string") return null;
  const workspaceId = value.trim();
  if (!workspaceId) return null;
  if (workspaceId.includes(",")) return null;
  if (workspaceId.toLowerCase() === "undefined" || workspaceId.toLowerCase() === "null") return null;
  return UUID_PATTERN.test(workspaceId) ? workspaceId : null;
}

const validWorkspaceId = "123e4567-e89b-12d3-a456-426614174000";
const secondWorkspaceId = "223e4567-e89b-12d3-a456-426614174000";

assert.equal(normalizeWorkspaceId(validWorkspaceId), validWorkspaceId);
assert.equal(normalizeWorkspaceId(` ${validWorkspaceId} `), validWorkspaceId);
assert.equal(normalizeWorkspaceId(`${validWorkspaceId},${secondWorkspaceId}`), null);
assert.equal(normalizeWorkspaceId([validWorkspaceId]), null);
assert.equal(normalizeWorkspaceId({ workspace_id: validWorkspaceId }), null);
assert.equal(normalizeWorkspaceId(""), null);
assert.equal(normalizeWorkspaceId("undefined"), null);
assert.equal(normalizeWorkspaceId("null"), null);

const apiSource = readFileSync(new URL("../src/services/api.ts", import.meta.url), "utf8");
assert.equal(apiSource.includes("headers.append"), false, "API client must not append workspace headers");
assert.match(apiSource, /headers\.delete\(WORKSPACE_HEADER\)/, "API client must remove incoming workspace header before setting one");
assert.match(apiSource, /headers\.set\(WORKSPACE_HEADER, workspaceId\)/, "API client must set exactly one normalized workspace header");
assert.match(apiSource, /normalizeWorkspaceId\(authStorage\.getCurrentWorkspaceId\(\)\)/, "API client must normalize persisted workspace before requests");

const authSource = readFileSync(new URL("../src/stores/auth.store.tsx", import.meta.url), "utf8");
assert.match(authSource, /normalizeWorkspaceId\(selectedWorkspace\?\.workspace_id\)/, "Auth restore must normalize selected membership workspace_id");
assert.match(authSource, /normalizeWorkspaceId\(workspaceId\)/, "Workspace switching must normalize selected workspace_id");

const topbarSource = readFileSync(new URL("../src/components/app-topbar.tsx", import.meta.url), "utf8");
assert.match(topbarSource, /value=\{membership\.workspace_id\}/, "Workspace selector must save membership.workspace_id only");

console.log("workspace header regression checks passed");
