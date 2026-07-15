import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.cwd());
const checks = [
  ["/settings/workspace route/page exists", "frontend/src/app/settings/workspace/page.tsx"],
  ["/settings/team route/page exists", "frontend/src/app/settings/team/page.tsx"],
  ["workspace switcher exists", "frontend/src/components/workspace-switcher.tsx"],
];
const requiredText = [
  ["create workspace UI exists", "frontend/src/i18n/messages/uk.json", "Створити робочий простір"],
  ["add user modal exists", "frontend/src/i18n/messages/uk.json", "Додати користувача"],
  ["role labels OWNER/MANAGER/ANALYST exist", "frontend/src/services/workspaces.ts", "OWNER"],
  ["duplicate user Ukrainian error exists", "backend/app/services/workspace_service.py", "Користувач уже доданий до команди."],
  ["last OWNER protection message exists", "frontend/src/i18n/messages/uk.json", "Не можна змінити або деактивувати останнього активного власника"],
  ["X-Workspace-ID usage exists in API client", "frontend/src/services/api.ts", "X-Workspace-ID"],
  ["no raw temporary_password returned in schemas", "backend/app/schemas/workspace.py", "temporary_password"],
];
let failed = false;
for (const [label, rel] of checks) {
  if (!fs.existsSync(path.join(root, rel))) { console.error(`FAIL ${label}`); failed = true; } else console.log(`OK ${label}`);
}
for (const [label, rel, text] of requiredText) {
  const value = fs.readFileSync(path.join(root, rel), "utf8");
  if (!value.includes(text)) { console.error(`FAIL ${label}`); failed = true; } else console.log(`OK ${label}`);
}
const changedText = ["backend/app", "frontend/src"].flatMap((rel) => fs.existsSync(path.join(root, rel)) ? fs.readdirSync(path.join(root, rel), { recursive: true }).map((file) => path.join(root, rel, file)).filter((file) => fs.statSync(file).isFile()).map((file) => fs.readFileSync(file, "utf8")) : [] ).join("\n");
if (/smtp|email invitation|send invitation/i.test(changedText)) { console.error("FAIL no email invitation/SMTP code was added"); failed = true; } else console.log("OK no email invitation/SMTP code was added");
if (failed) process.exit(1);
