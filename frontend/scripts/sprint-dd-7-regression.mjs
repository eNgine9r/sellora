import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.cwd());
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
const exists = (file) => fs.existsSync(path.join(root, file));
const failures = [];
const assert = (condition, message) => { if (!condition) failures.push(message); };

const settings = read("frontend/src/app/settings/page.tsx");
const workspace = read("frontend/src/app/settings/workspace/page.tsx");
const team = read("frontend/src/app/settings/team/page.tsx");
const importPage = read("frontend/src/app/settings/import/page.tsx");
const integrations = read("frontend/src/app/settings/integrations/page.tsx");
const overlay = read("frontend/src/components/ui/overlay.tsx");
const crm = read("frontend/src/components/crm-workspace.tsx");
const uk = read("frontend/src/i18n/messages/uk.json");
const en = read("frontend/src/i18n/messages/en.json");

assert(settings.includes("WorkspacePage") && settings.includes("WorkspaceHeader"), "/settings must use protected workspace foundation.");
assert(workspace.includes("WorkspacePage") && workspace.includes("FormField") && workspace.includes("Input") && workspace.includes("Select"), "Workspace settings must use shared form primitives.");
assert(team.includes("WorkspacePage") && team.includes("DataTable") && team.includes("PaginationControls"), "Team page must use workspace table and bottom pagination patterns.");
assert(team.indexOf("DataTable") < team.indexOf("PaginationControls"), "Team pagination must appear below the list/table.");
assert(team.includes("ConfirmationDialog") && !team.includes("confirm("), "Team destructive actions must use ConfirmationDialog and not browser confirm().");
assert(team.includes("lg:table") && team.includes("lg:hidden"), "Team page must include desktop table and mobile cards.");
assert(team.includes("currentUser") && team.includes("lastOwner"), "Team page must keep current-user and last-owner safety guards.");
assert(importPage.includes("WorkspacePage") && importPage.includes("WorkspaceHeader"), "Import Center must use Settings workspace header pattern.");
assert(integrations.includes("WorkspacePage") && integrations.includes("WorkspaceHeader"), "Integrations page must use Settings workspace header pattern.");

for (const href of ["/settings/workspace", "/settings/team", "/settings/import", "/settings/integrations", "/settings/feedback"]) {
  assert(settings.includes(href), `Settings overview must link real route ${href}.`);
  assert(exists(`frontend/src/app${href}/page.tsx`), `Settings overview links missing route ${href}.`);
}
assert(!settings.includes("/settings/billing") && !settings.includes("/settings/security"), "Settings overview must not link unsupported routes.");
assert(!/api[_-]?key|access[_-]?token|DATABASE_URL|JWT/i.test(settings), "Settings overview must not render secrets or token names.");
assert(!/api[_-]?key|access[_-]?token|DATABASE_URL|JWT/i.test(team), "Team UI must not render secrets or token names.");
assert(uk.includes('"OWNER"') && uk.includes('"MANAGER"') && uk.includes('"ANALYST"'), "Ukrainian role translations must preserve backend role enum keys.");
assert(en.includes('"OWNER"') && en.includes('"MANAGER"') && en.includes('"ANALYST"'), "English role translations must preserve backend role enum keys.");
assert(settings.includes("bg-surface") && workspace.includes("bg-surface") && team.includes("bg-surface"), "Settings pages must use semantic surface classes.");
assert(!settings.includes("max-w-6xl") && !workspace.includes("max-w-4xl") && !team.includes("max-w-6xl"), "Settings pages must not restore centered protected max-width shells.");
assert(overlay.includes("Drawer") && crm.includes("EntitySidePanel") && crm.includes("data-workspace-split-view"), "Drawer and EntitySidePanel foundations must remain available.");
assert(crm.includes('layout === "five-balanced"'), "Five-card balanced summary support must remain intact.");
for (const route of ["dashboard", "orders", "products", "inventory", "shipments", "advertising", "finance", "analytics", "settings"]) {
  assert(exists(`frontend/src/app/${route}/page.tsx`), `Required route /${route} must exist.`);
}
assert(!/function SettingsCard|function SettingsButton|function SettingsInput/.test(settings + workspace + team), "Do not add duplicate page-local Settings primitives.");

if (failures.length) {
  console.error("Sprint Dd.7 regression failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}
console.log("Sprint Dd.7 regression checks passed.");
