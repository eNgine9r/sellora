import fs from "node:fs";

const read = (path) => fs.readFileSync(path, "utf8");
const exists = (path) => fs.existsSync(path);
const checks = [];
const expect = (name, condition) => checks.push({ name, passed: Boolean(condition) });

const paths = {
  freeze: "docs/advertising-4x-freeze-and-handoff.md",
  blockers: "docs/advertising-known-blockers.md",
  finance: "docs/finance-part-5-handoff.md",
  readme: "README.md",
  readiness: "docs/mvp-readiness.md",
  limitations: "docs/known-limitations.md",
  metrics: "docs/advertising-metrics.md",
  importGuide: "docs/advertising-import-guide.md",
  pilotGuide: "docs/pilot-advertising-guide.md",
  stagingChecklist: "docs/staging-qa-checklist.md",
  pilotChecklist: "docs/pilot-qa-checklist.md",
  metaPlan: "docs/meta-ads-integration-plan.md",
  metaDesign: "docs/meta-ads-technical-design.md",
};

for (const path of Object.values(paths)) expect(`${path} exists`, exists(path));

const freeze = exists(paths.freeze) ? read(paths.freeze) : "";
const blockers = exists(paths.blockers) ? read(paths.blockers) : "";
const finance = exists(paths.finance) ? read(paths.finance) : "";
const docs = Object.values(paths).filter(exists).map(read).join("\n");

const requiredBlockers = [
  "B-ADV-001",
  "B-ADV-002",
  "B-ADV-003",
  "B-ADV-004",
  "B-ADV-005",
  "B-ADV-006",
  "B-ADV-007",
  "B-ADV-008",
  "B-ADV-009",
  "B-ADV-010",
];

expect("Advertising 4.x feature-frozen", docs.includes("Advertising is feature-frozen for now") && freeze.includes("feature-frozen"));
expect("architecture-ready locally validated not pilot-ready", docs.includes("architecture-ready / locally validated / feature-frozen / not pilot-ready"));
expect("known blockers registry", requiredBlockers.every((id) => blockers.includes(id)) && blockers.includes("Blocks pilot readiness"));
expect("Part 5 handoff document", finance.includes("Finance Part 5 Handoff") && finance.includes("Part 5 rule"));
expect("manual CSV active source", docs.includes("Manual/CSV remains the active source") || docs.includes("manual entry / CSV import"));
expect("Meta Ads API not active", docs.includes("Meta Ads API — mock/future-ready / not active") && docs.includes("Meta Ads API remains not active"));
expect("live OAuth future work", docs.includes("Live OAuth/token storage/apply-sync are future work") || docs.includes("live Meta OAuth"));
expect("token storage future work", docs.includes("token storage") && docs.includes("future work"));
expect("apply-sync future work", docs.includes("apply-sync") && docs.includes("future work"));
expect("runtime staging blockers tracked", docs.includes("Runtime/staging blockers are tracked separately") && blockers.includes("runtime/staging"));
expect("Sprint 4.10 pending runtime QA", docs.includes("Sprint 4.10 runtime PostgreSQL migration QA remains pending"));
expect("Sprint 4.12 conditional browser QA note", docs.includes("Sprint 4.12 browser/mobile QA remains pending"));
expect("Sprint 4.4 blockers", docs.includes("Sprint 4.4 PostgreSQL runtime/staging/browser QA blockers remain open"));
expect("advertising import not pilot-ready", docs.includes("Advertising import is not pilot-ready") || docs.includes("advertising import is not pilot-ready"));
expect("Finance treats Advertising as conditional manual CSV source", finance.includes("conditional manual/CSV source") && docs.includes("Part 5 may use Advertising data only as conditional manual/CSV source"));
expect("readiness matrix", freeze.includes("Readiness matrix") && freeze.includes("Pilot-ready ❌ No"));
expect("freeze rules", freeze.includes("Allowed after freeze") && freeze.includes("Not allowed after freeze"));
expect("no live Meta implementation claim", !/Meta Ads API — active|Advertising 4\.x — pilot-ready|Advertising import is pilot-ready/.test(docs));
expect("no new migration marker", !/revision = .*freeze|op\.create_table\(["']meta_ad_connections/.test(docs));

const failed = checks.filter((check) => !check.passed);
if (failed.length) {
  console.error("Advertising freeze handoff regression failed:");
  for (const check of failed) console.error(`- ${check.name}`);
  process.exit(1);
}

console.log(`Advertising freeze handoff regression passed (${checks.length} checks).`);
