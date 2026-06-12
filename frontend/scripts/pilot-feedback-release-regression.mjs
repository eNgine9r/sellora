import { readFileSync } from "node:fs";

const files = {
  topbar: readFileSync("frontend/src/components/app-topbar.tsx", "utf8"),
  dialog: readFileSync("frontend/src/components/feedback-dialog.tsx", "utf8"),
  feedbackPage: readFileSync("frontend/src/app/settings/feedback/page.tsx", "utf8"),
  feedbackService: readFileSync("frontend/src/services/feedback.ts", "utf8"),
  backendApi: readFileSync("backend/app/api/v1/feedback.py", "utf8"),
  backendModel: readFileSync("backend/app/models/pilot_feedback.py", "utf8"),
  en: readFileSync("frontend/src/i18n/messages/en.json", "utf8"),
  uk: readFileSync("frontend/src/i18n/messages/uk.json", "utf8"),
  processDocs: readFileSync("docs/pilot-feedback-process.md", "utf8"),
  releaseChecklist: readFileSync("docs/pre-mvp-release-checklist.md", "utf8"),
  limitations: readFileSync("docs/known-limitations.md", "utf8"),
  releaseNotes: readFileSync("docs/pilot-release-notes.md", "utf8"),
  stagingQa: readFileSync("docs/staging-qa-checklist.md", "utf8"),
  pilotQa: readFileSync("docs/pilot-qa-checklist.md", "utf8"),
  tests: readFileSync("backend/tests/test_feedback.py", "utf8"),
};

const docs = files.processDocs + files.releaseChecklist + files.limitations + files.releaseNotes + files.stagingQa + files.pilotQa;
const checks = [
  ["feedback button/form", files.topbar.includes("FeedbackDialog") && files.dialog.includes("textarea") && files.dialog.includes("submitPilotFeedback")],
  ["feedback i18n keys", files.en.includes('"feedback"') && files.uk.includes('"feedback"') && files.en.includes('"pilotFeedback"')],
  ["feedback privacy hint", files.dialog.includes("privacyHint") && files.uk.includes("Не додавайте паролі")],
  ["feedback submit loading/success/error states", files.dialog.includes('"submitting"') && files.dialog.includes('"success"') && files.dialog.includes('"error"')],
  ["settings feedback route", files.feedbackPage.includes("fetchPilotFeedback") && files.feedbackPage.includes("updatePilotFeedbackStatus")],
  ["backend feedback storage", files.backendModel.includes("pilot_feedback") && files.backendApi.includes("/feedback")],
  ["pilot feedback process docs", files.processDocs.includes("Severity levels") && files.processDocs.includes("Triage workflow")],
  ["pre-MVP release checklist docs", files.releaseChecklist.includes("Pre-MVP Release Checklist") && files.releaseChecklist.toLowerCase().includes("backup/rollback")],
  ["known limitations docs", files.limitations.includes("Instagram Direct API is not connected yet") && files.limitations.includes("Feedback attachments")],
  ["pilot release notes docs", files.releaseNotes.includes("Pilot Release Notes") && files.releaseNotes.includes("Як повідомляти фідбек")],
  ["mobile QA markers", docs.includes("375px") && docs.includes("feedback modal") || docs.includes("Feedback modal")],
  ["empty/loading/error final pass markers", files.stagingQa.includes("Empty/loading/error final pass") && files.dialog.includes("disabled={status ===")],
  ["privacy guardrails", docs.includes("API keys") && docs.includes("tokens") && docs.includes("workspace IDs")],
  ["no real private data", !/\+380\d{9}|@gmail\.com|@ukr\.net|Authorization: Bearer/i.test(docs + files.dialog)],
  ["backend feedback tests", files.tests.includes("test_feedback_create_requires_message") && files.tests.includes("workspace_scoped")],
];

const failed = checks.filter(([, ok]) => !ok);
if (failed.length) {
  console.error(`Pilot feedback release regression failed: ${failed.map(([name]) => name).join(", ")}`);
  process.exit(1);
}
console.log(`Pilot feedback release regression passed (${checks.length} checks).`);
