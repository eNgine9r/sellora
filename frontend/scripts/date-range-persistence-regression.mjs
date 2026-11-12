import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const ts = require("typescript");
const read = (path) => readFileSync(path, "utf8");

const lib = read("frontend/src/lib/date-range-presets.ts");
const compiled = ts.transpileModule(lib, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText;
const exports = {};
new Function("exports", compiled)(exports);
const { dateRangeForPreset, restoreDateRange, previousDateRange } = exports;

const atNoon = new Date(2026, 10, 12, 12, 0);
assert.deepEqual(restoreDateRange(null, atNoon), { preset: "thisMonth", date_from: "2026-11-01", date_to: "2026-11-12" });
assert.deepEqual(restoreDateRange("invalid-json", atNoon), dateRangeForPreset("thisMonth", atNoon));
assert.deepEqual(restoreDateRange('{"preset":"invalid"}', atNoon), dateRangeForPreset("thisMonth", atNoon));
assert.deepEqual(restoreDateRange('{"preset":"last7","date_from":"2023-01-01","date_to":"2023-01-30"}', atNoon),
  dateRangeForPreset("last7", atNoon), "rolling preset dates must refresh instead of restoring outdated dates");
assert.deepEqual(restoreDateRange('{"preset":"thisMonth","date_from":"2025-06-01"}', new Date(2026, 11, 2, 12)),
  { preset: "thisMonth", date_from: "2026-12-01", date_to: "2026-12-02" });
assert.deepEqual(restoreDateRange('{"preset":"custom","date_from":"2026-09-03","date_to":"2026-10-15"}', atNoon),
  { preset: "custom", date_from: "2026-09-03", date_to: "2026-10-15" });
for (const bad of [
  '{"preset":"custom","date_from":"","date_to":""}',
  '{"preset":"custom","date_from":"2026-11-31","date_to":"2026-12-01"}',
  '{"preset":"custom","date_from":"2026-12-01","date_to":"2026-11-01"}',
  '{"preset":"custom","date_from":"2026-11-01"}',
  '{"preset":"custom","date_from":"not-a-date","date_to":"2026-12-01"}',
]) {
  assert.deepEqual(restoreDateRange(bad, atNoon), dateRangeForPreset("thisMonth", atNoon));
}
assert.deepEqual(previousDateRange({ preset: "thisMonth", date_from: "2026-11-01", date_to: "2026-11-12" }),
  { preset: "thisMonth", date_from: "2026-10-20", date_to: "2026-10-31" });

const beforeTimezone = process.env.TZ;
try {
  process.env.TZ = "Pacific/Kiritimati";
  assert.deepEqual(dateRangeForPreset("thisMonth", new Date("2026-11-01T00:30:00+14:00")),
    { preset: "thisMonth", date_from: "2026-11-01", date_to: "2026-11-01" });
  process.env.TZ = "America/Los_Angeles";
  assert.deepEqual(dateRangeForPreset("thisMonth", new Date("2026-11-01T23:30:00-08:00")),
    { preset: "thisMonth", date_from: "2026-11-01", date_to: "2026-11-01" });
} finally {
  if (beforeTimezone === undefined) delete process.env.TZ;
  else process.env.TZ = beforeTimezone;
}

const provider = read("frontend/src/providers/date-range-provider.tsx");
const selector = read("frontend/src/components/date-range-selector.tsx");
const dashboard = read("frontend/src/app/dashboard/page.tsx");
const analytics = read("frontend/src/app/analytics/page.tsx");
const insights = read("frontend/src/app/insights/page.tsx");
assert(provider.includes('DATE_RANGE_STORAGE_KEY = "sellora:date-range:v1"'));
assert(provider.includes('window.localStorage.getItem(DATE_RANGE_STORAGE_KEY)') && provider.includes('window.localStorage.setItem(DATE_RANGE_STORAGE_KEY'));
assert(provider.includes('dateRangeForPreset("thisMonth")'));
assert(provider.includes('next.preset === "custom" ? next : { preset: next.preset }'), "only custom dates are stored as fixed dates");
assert(provider.includes("setIsReady(true)") && provider.includes("isReady"), "hydration protected");
assert(provider.includes('"focus"') && provider.includes('"visibilitychange"') && provider.includes("refreshRollingPreset"));
assert(selector.includes('dateRangeForPreset("thisMonth")') && selector.includes("sharedRange.isReady"));
for (const [page, source] of [["dashboard",dashboard],["analytics",analytics],["insights",insights]]) {
  assert(source.includes("isReady: periodReadyFromStorage") && source.includes("const enabled = periodReadyFromStorage"),
    page + " must not query wrong transient default dates before restoring storage");
}
console.log("Persisted date range regression PASS (month, custom, timezone, rollover, hydrate, query gating).");
