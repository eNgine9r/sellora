import fs from "node:fs";
import path from "node:path";

const outputRoot = path.resolve(process.cwd(), "artifacts/mobile-ui-audit");
const reportPath = path.join(outputRoot, "report.json");
const report = JSON.parse(fs.readFileSync(reportPath, "utf8"));

for (const viewport of report.viewports ?? []) {
  for (const entry of viewport.routes ?? []) {
    if (entry.status === "ERROR") continue;
    const pageOverflow = Number(entry.overflow?.documentOverflow ?? 0);
    const dialogFailure = Boolean(entry.dialog && (!entry.dialog.withinViewport || Number(entry.dialog.horizontalOverflow ?? 0) > 1));
    entry.intentionalScrollableElements = entry.overflow?.offenders?.length ?? 0;
    entry.status = pageOverflow > 1 || dialogFailure ? "ISSUE" : "PASS";
  }
}

fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
const lines = [
  "# Sellora Mobile UI Audit",
  "",
  `Generated: ${report.generatedAt}`,
  `Base URL: ${report.baseUrl}`,
  `Authenticated: ${report.authenticated ? "yes" : "no"}`,
  report.fatalError ? `Fatal error: ${report.fatalError}` : "",
  "",
  "Intentional horizontal table/tab scrollers are recorded for manual review but are not classified as page overflow.",
  "",
  "| Viewport | Route | Status | Page overflow | Dialog | Scrollable descendants |",
  "|---|---|---|---:|---|---:|",
].filter(Boolean);
for (const viewport of report.viewports ?? []) {
  for (const entry of viewport.routes ?? []) {
    lines.push(`| ${viewport.name} | \`${entry.route}\` | ${entry.status} | ${entry.overflow?.documentOverflow ?? "—"} px | ${entry.dialog ? (entry.dialog.withinViewport && Number(entry.dialog.horizontalOverflow ?? 0) <= 1 ? "PASS" : "OUTSIDE") : "not opened"} | ${entry.intentionalScrollableElements ?? 0} |`);
  }
}
fs.writeFileSync(path.join(outputRoot, "report.md"), `${lines.join("\n")}\n`);

const failures = (report.viewports ?? []).flatMap((viewport) => viewport.routes ?? []).filter((entry) => entry.status !== "PASS");
console.log(`Normalized mobile UI report: ${failures.length} page/dialog failures.`);
if (failures.length) process.exit(1);
