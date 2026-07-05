import { readFileSync } from "node:fs";

const page = readFileSync("frontend/src/app/finance/page.tsx", "utf8");
const docs = readFileSync("docs/finance-readiness.md", "utf8") + readFileSync("docs/known-limitations.md", "utf8");
const checks = [
  ["mobile page wrapper prevents x overflow", page.includes("overflow-x-hidden") && page.includes("sellora-mobile-page")],
  ["KPI cards stack on mobile", page.includes("sm:grid-cols-2") && page.includes("xl:grid-cols-4")],
  ["adjustment form stacks before desktop grid", page.includes("md:grid-cols-4") && page.includes("data-finance-adjustment-form")],
  ["adjustment rows avoid mobile table overflow", page.includes("md:grid-cols-[1fr_auto]") && page.includes("flex flex-wrap")],
  ["warning panel marker exists", page.includes("data-finance-data-quality-warnings")],
  ["static coverage is not browser QA", docs.includes("static regression scripts are not screenshot QA") || docs.includes("Static checks")],
];
let failed = false;
for (const [label, ok] of checks) {
  if (!ok) {
    console.error(`Finance mobile static QA regression failed: ${label}`);
    failed = true;
  }
}
if (failed) process.exit(1);
console.log(`Finance mobile static QA regression passed (${checks.length} checks; not browser QA).`);
