import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const read = (rel) => fs.readFileSync(path.join(root, rel), "utf8");
const exists = (rel) => fs.existsSync(path.join(root, rel));
const checks = [
  ["profile menu component exists", exists("frontend/src/components/profile-menu.tsx")],
  ["mobile more sheet component exists", exists("frontend/src/components/mobile-more-sheet.tsx")],
  ["overlay portal usage exists", read("frontend/src/components/profile-menu.tsx").includes("<Portal>") && read("frontend/src/components/ui/bottom-sheet.tsx").includes("<Portal>")],
  ["workspace switcher integrated into profile/mobile menu", read("frontend/src/components/profile-menu.tsx").includes("<WorkspaceSwitcher") && read("frontend/src/components/mobile-more-sheet.tsx").includes("<WorkspaceSwitcher")],
  ["create workspace action is still reachable", read("frontend/src/components/workspace-menu-content.tsx").includes("createWorkspace")],
  ["single mobile profile entry point", !read("frontend/src/components/app-topbar.tsx").includes("MoreHorizontal") && read("frontend/src/components/app-shell.tsx").includes('aria-haspopup="dialog"')],
  ["profile header is localized", read("frontend/src/components/mobile-more-sheet.tsx").includes('title={t("accountMenu.profile")}')],
  ["workspace switcher hides extra workspaces until requested", read("frontend/src/components/workspace-menu-content.tsx").includes("showWorkspaces ?") && read("frontend/src/components/workspace-menu-content.tsx").includes("otherWorkspaces")],
  ["create workspace form is collapsed by default", read("frontend/src/components/workspace-menu-content.tsx").includes("showCreate ?") && read("frontend/src/components/workspace-menu-content.tsx").includes("setShowCreate(true)")],
  ["membership roles are localized", read("frontend/src/components/workspace-switcher.tsx").includes("accountMenu.roleOwner") && read("frontend/src/i18n/messages/en.json").includes('"roleManager": "Manager"')],
  ["Direct, feedback and preferences remain accessible", read("frontend/src/components/mobile-more-sheet.tsx").includes('href="/direct"') && read("frontend/src/components/mobile-more-sheet.tsx").includes("<FeedbackDialog") && read("frontend/src/components/mobile-more-sheet.tsx").includes("<ThemeToggle")],

  ["logout action is still reachable", read("frontend/src/components/profile-menu.tsx").includes("onLogout") && read("frontend/src/components/mobile-more-sheet.tsx").includes("onLogout")],
  ["duplicate standalone workspace selector removed from topbar", !read("frontend/src/components/app-topbar.tsx").includes("<WorkspaceSwitcher")],
  ["bottom sheet labels exist", read("frontend/src/i18n/messages/uk.json").includes("Швидкі дії") && read("frontend/src/i18n/messages/uk.json").includes("Більше")],
  ["Ukrainian labels exist", read("frontend/src/i18n/messages/uk.json").includes("Профіль") && read("frontend/src/i18n/messages/uk.json").includes("Створити робочий простір")],
  ["no Meta-specific changes added in topbar overlay files", !/meta/i.test(read("frontend/src/components/profile-menu.tsx") + read("frontend/src/components/mobile-more-sheet.tsx") + read("frontend/src/components/workspace-menu-content.tsx"))],
];
let failed = false;
for (const [label, ok] of checks) {
  if (ok) console.log(`OK ${label}`);
  else { console.error(`FAIL ${label}`); failed = true; }
}
if (failed) process.exit(1);
