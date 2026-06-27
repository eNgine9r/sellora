import { readFileSync } from "node:fs";

const files = {
  dashboard: readFileSync("frontend/src/app/dashboard/page.tsx", "utf8"),
  pilotComponent: readFileSync("frontend/src/components/pilot-readiness.tsx", "utf8"),
  importPage: readFileSync("frontend/src/app/settings/import/page.tsx", "utf8"),
  en: readFileSync("frontend/src/i18n/messages/en.json", "utf8"),
  uk: readFileSync("frontend/src/i18n/messages/uk.json", "utf8"),
  onboarding: readFileSync("docs/pilot-onboarding-guide.md", "utf8"),
  demoScript: readFileSync("docs/demo-script.md", "utf8"),
  pilotQa: readFileSync("docs/pilot-qa-checklist.md", "utf8"),
  readiness: readFileSync("docs/mvp-readiness.md", "utf8"),
  stagingQa: readFileSync("docs/staging-qa-checklist.md", "utf8"),
  imports: readFileSync("docs/imports.md", "utf8"),
  demoDataset: readFileSync("docs/demo-dataset.md", "utf8"),
};

const combinedDocs = files.onboarding + files.demoScript + files.pilotQa + files.readiness + files.stagingQa + files.imports + files.demoDataset;
const checks = [
  ["demo workspace notice", files.pilotComponent.includes("DemoWorkspaceNotice") && files.dashboard.includes("DemoWorkspaceNotice") && files.pilotComponent.includes("sellora-demo")],
  ["onboarding setup checklist", files.pilotComponent.includes("SetupChecklist") && files.dashboard.includes("setupItems")],
  ["first-run empty state CTAs", files.pilotComponent.includes("FirstRunEmptyCtas") && files.dashboard.includes("isFirstRun")],
  ["Import Center pilot helper text", files.pilotComponent.includes("ImportPilotHelp") && files.importPage.includes("ImportPilotHelp") && files.imports.includes("dry-run validates")],
  ["pilot onboarding docs", files.onboarding.includes("Пілотний onboarding guide") && files.onboarding.includes("Instagram Direct API ще не підключено")],
  ["demo script docs", files.demoScript.includes("Demo flow") && files.demoScript.includes("Pilot feedback questions")],
  ["pilot QA checklist docs", files.pilotQa.includes("Expected result:") && files.pilotQa.includes("Mobile QA")],
  ["MVP readiness docs", files.readiness.includes("Known limitations") && files.readiness.includes("Meta Ads API is not connected yet")],
  ["mobile overflow checklist docs", files.stagingQa.includes("375px") && files.stagingQa.includes("No body-level horizontal overflow") || files.pilotQa.includes("No body-level horizontal overflow")],
  ["i18n keys", files.en.includes('"demoWorkspace"') && files.uk.includes('"demoWorkspace"') && files.en.includes('"setupChecklist"') && files.uk.includes('"importHelp"')],
  ["privacy guardrails", combinedDocs.includes("Не показуйте приватні") || combinedDocs.includes("без приватних")],
  ["no real private demo data", !/\+380\d{9}|@gmail\.com|@ukr\.net|Workspace ID:/i.test(combinedDocs)],
];

const failed = checks.filter(([, ok]) => !ok);
if (failed.length) {
  console.error(`Pilot readiness regression failed: ${failed.map(([name]) => name).join(", ")}`);
  process.exit(1);
}
console.log(`Pilot readiness regression passed (${checks.length} checks).`);
