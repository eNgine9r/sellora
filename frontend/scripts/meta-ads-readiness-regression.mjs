import fs from "node:fs";

const read = (path) => fs.readFileSync(path, "utf8");
const checks = [];
const expect = (name, condition) => checks.push({ name, passed: Boolean(condition) });

const plan = read("docs/meta-ads-integration-plan.md");
const technical = read("docs/meta-ads-technical-design.md");
const privacy = read("docs/meta-ads-privacy-safety.md");
const metrics = read("docs/advertising-metrics.md");
const limitations = read("docs/known-limitations.md");
const readiness = read("docs/mvp-readiness.md");
const importGuide = read("docs/advertising-import-guide.md");
const stagingQa = read("docs/staging-qa-checklist.md");
const pilotQa = read("docs/pilot-qa-checklist.md");
const readme = read("README.md");
const combined = [plan, technical, privacy, metrics, limitations, readiness, importGuide, stagingQa, pilotQa, readme].join("\n");

expect("Meta Ads API is future-work, not active", combined.includes("planned / architecture-ready / not active") && combined.includes("live Meta OAuth") && combined.includes("not active"));
expect("manual and CSV import remain current MVP source", combined.includes("manual entry / CSV import") && combined.includes("Manual entry and CSV import remain") && combined.includes("current MVP advertising data source"));
expect("OAuth architecture is documented", plan.includes("OAuth architecture contract") && plan.includes("Callback validates the state") && plan.includes("short-lived") && plan.includes("long-lived"));
expect("OWNER-only connection is documented", combined.includes("Only OWNER can connect/disconnect") && combined.includes("OWNER-only"));
expect("encrypted token requirement is documented", combined.includes("encrypted before storage") && combined.includes("encrypted at rest") && technical.includes("Token encryption approach"));
expect("workspace isolation is documented", combined.includes("A Meta connection belongs to exactly one workspace") && combined.includes("Workspace A cannot") && combined.includes("workspace_id"));
expect("no live implementation claim", !combined.includes("Meta Ads API is implemented") && !combined.includes("live Meta integration works"));
expect("no real token/account fixtures", !/EA[A-Za-z0-9]{20,}|act_\d{8,}|Authorization: Bearer\s+[A-Za-z0-9._-]+/.test(combined));
expect("no pilot-ready claim", limitations.includes("Advertising import remains not pilot-ready") && readiness.includes("advertising import is not pilot-ready"));
expect("Conversions API is separate future phase with legal/privacy review", combined.includes("Conversions API") && combined.includes("legal/privacy review"));
expect("Sprint 4.4 blocker remains documented", combined.includes("Sprint 4.4") && combined.includes("PostgreSQL runtime") && combined.includes("browser/mobile"));
expect("read-only Meta sync data ownership is documented", combined.includes("delivery metrics only") && combined.includes("Orders and profit still come from Sellora data"));
expect("future DB proposal has no migration", plan.includes("no migration in Sprint 4.6") && plan.includes("meta_sync_runs"));
expect("technical boundaries avoid live modules", technical.includes("future implementation contract") && technical.includes("fake client in tests"));

const failed = checks.filter((check) => !check.passed);
if (failed.length) {
  console.error("Meta Ads readiness regression failed:");
  for (const check of failed) console.error(`- ${check.name}`);
  process.exit(1);
}

console.log(`Meta Ads readiness regression passed (${checks.length} checks).`);
