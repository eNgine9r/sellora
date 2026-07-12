import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const read = (rel) => fs.readFileSync(path.join(root, rel), "utf8");
const exists = (rel) => fs.existsSync(path.join(root, rel));
const checks = [
  ["workspace switcher exists", exists("frontend/src/components/workspace-switcher.tsx")],
  ["profile menu workspace controls exist", read("frontend/src/components/profile-menu.tsx").includes("<WorkspaceSwitcher")],
  ["mobile more sheet exists", exists("frontend/src/components/mobile-more-sheet.tsx")],
  ["/settings/workspace exists", exists("frontend/src/app/settings/workspace/page.tsx")],
  ["/settings/team exists", exists("frontend/src/app/settings/team/page.tsx")],
  ["add user modal exists", read("frontend/src/app/settings/team/page.tsx").includes("settings.teamPage.addAction") && read("frontend/src/i18n/messages/uk.json").includes("Додати користувача")],
  ["duplicate user error exists", read("backend/app/services/workspace_service.py").includes("Користувач уже доданий до команди.")],
  ["last OWNER protection exists", read("backend/app/services/workspace_service.py").includes("останнього власника")],
  ["access denied labels exist", read("frontend/src/app/settings/workspace/page.tsx").includes("settings.ownerOnly") && read("frontend/src/app/settings/team/page.tsx").includes("settings.teamPage.restricted") && read("frontend/src/i18n/messages/uk.json").includes("У вас немає доступу")],
  ["onboarding empty workspace copy exists", read("frontend/src/i18n/messages/uk.json").includes("У вас ще немає робочого простору")],
  ["no Meta-specific changes were added to SaaS admin QA files", !/meta/i.test(read("frontend/src/components/no-workspace-onboarding.tsx") + read("frontend/src/components/profile-menu.tsx") + read("frontend/src/components/mobile-more-sheet.tsx"))],
];
let failed = false;
for (const [label, ok] of checks) {
  if (ok) console.log(`OK ${label}`);
  else { console.error(`FAIL ${label}`); failed = true; }
}
if (failed) process.exit(1);
