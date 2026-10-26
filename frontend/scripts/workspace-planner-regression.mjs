import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const read = (path) => readFileSync(join(root, path), "utf8");
const calendar = read("src/app/calendar/page.tsx");
const notes = read("src/app/notes/page.tsx");
const insights = read("src/app/insights/page.tsx");
const client = read("src/services/workspace-memos.ts");
const uk = JSON.parse(read("src/i18n/messages/uk.json"));
const en = JSON.parse(read("src/i18n/messages/en.json"));
const checks = [
  ["calendar uses real workspace scoped memo/order/shipment sources", calendar.includes("fetchWorkspaceMemos") && calendar.includes("fetchOrders") && calendar.includes("fetchShipments")],
  ["calendar does not infer future shipments", calendar.includes("shipment.shipped_at") && calendar.includes("shipment.delivered_at") && !calendar.includes("estimated_delivery")],
  ["calendar has accessible month navigation and day filters", calendar.includes("prevMonth") && calendar.includes("nextMonth") && calendar.includes('role="grid"') && calendar.includes("eventsFilter")],
  ["notes support CRUD and workspace-specific cache", notes.includes("createWorkspaceMemo") && notes.includes("updateWorkspaceMemo") && notes.includes("deleteWorkspaceMemo") && notes.includes('["workspace-memos", workspaceId]')],
  ["notes protect writes by user role", notes.includes("canEdit") && notes.includes('role === "OWNER"') && notes.includes('role === "MANAGER"')],
  ["insights use API rules and report period", insights.includes("fetchBusinessInsights") && insights.includes("fetchSalesReport") && insights.includes("fetchAdvertisingReport") && insights.includes("useDateRange")],
  ["insights maintain permitted action links", insights.includes("allowedTargets") && insights.includes("BusinessInsight")],
  ["workspace memo service explicitly passes workspace ID", client.includes('"X-Workspace-ID"') && client.includes('"/workspace-memos"')],
  ["all three modules use theme-aware workspace pages", [calendar, notes, insights].every(content => content.includes("WorkspacePage") && !content.includes("bg-[#F8F7FC]"))],
  ["all three modules use production data not coming-soon filler", [calendar, notes, insights].every(content => !content.includes("analytics.comingSoon"))],
  ["uk/en planner and insight keys available", [uk, en].every(messages => messages.planner?.calendarSubtitle && messages.planner?.notesSubtitle && messages.insightHub?.subtitle && messages.insightHub?.loadError)],
];
let failed = false;
for (const [name, ok] of checks) {
  if (!ok) { console.error("FAILED", name); failed = true; }
}
if (failed) process.exitCode = 1;
else console.log(`Workspace planner regression PASS (${checks.length} checks)`);
