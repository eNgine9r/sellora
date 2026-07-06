import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.cwd());
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
const exists = (file) => fs.existsSync(path.join(root, file));

const reportPath = "docs/sprint-7c-dashboard-owner-experience.md";
const report = exists(reportPath) ? read(reportPath) : "";
const dashboardPage = read("frontend/src/app/dashboard/page.tsx");
const uk = read("frontend/src/i18n/messages/uk.json");
const migrationFiles = fs.readdirSync(path.join(root, "backend/alembic/versions"));

const checks = [
  ["Sprint 7C QA report exists", exists(reportPath)],
  ["dashboard period copy exists", uk.includes("Показники розраховані за вибраний період") && dashboardPage.includes("selectedPeriodLabel")],
  ["KPI helper copy exists", uk.includes("За вибраний період замовлень ще немає") && dashboardPage.includes("kpiHelpers")],
  ["lead funnel copy exists", uk.includes("Воронка продажів") && uk.includes("Ліди") && uk.includes("Доставлено") && dashboardPage.includes("dashboard.funnel.title")],
  ["recent orders clarification exists", uk.includes("незалежно від вибраного періоду")],
  ["advertising snapshot copy exists", uk.includes("Оцінюйте витрати, замовлення та окупність реклами") && uk.includes("Рекламних даних за вибраний період ще немає")],
  ["finance/profit missing-data copy exists", uk.includes("Прибуток ще не розраховано") && uk.includes("Перевірте собівартість товарів")],
  ["inventory/low-stock alert copy exists", uk.includes("Низький залишок") && uk.includes("Додайте товари або імпортуйте каталог")],
  ["actionable alerts copy exists", uk.includes("Що потребує уваги") && dashboardPage.includes("ownerAlerts")],
  ["abbreviation explanations exist", uk.includes("ROAS — окупність реклами") && uk.includes("CPA — ціна замовлення") && uk.includes("AOV — середній чек")],
  ["mobile dashboard notes exist", report.includes("375px") && report.includes("390px") && report.includes("430px") && report.includes("768px")],
  ["no Meta-specific feature work was added", report.includes("No Meta") || report.includes("No backend") || !/Meta OAuth changes added|scheduled sync added|apply-sync added/i.test(report)],
  ["no new Sprint 7C migration file was added", migrationFiles.every((file) => !/7c|dashboard_owner|owner_experience/i.test(file)) && report.includes("No database migration was added")],
];

let failed = false;
for (const [label, ok] of checks) {
  if (ok) console.log(`OK ${label}`);
  else {
    failed = true;
    console.error(`FAIL ${label}`);
  }
}

if (failed) process.exit(1);
console.log("Dashboard owner experience regression checks passed.");
