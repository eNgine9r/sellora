# Advertising Staging QA — Sprint 4.2

Use only synthetic advertising data. The preferred test file is `docs/templates/advertising-import-template.csv` or the app download `/templates/advertising-import-template.csv`.

## Required QA Flow

1. Open `/settings/import`.
2. Select the Advertising import preset.
3. Upload the synthetic advertising template.
4. Run dry-run.
5. Confirm column mapping for `Дата`, `Кампанія`, `Платформа`, `Витрати`, `Повідомлення`, `Ліди`, `Замовлення`, `Дохід`, `Чистий прибуток`, `Покази`, and `Кліки`.
6. Confirm row-level warnings/errors if any.
7. Execute import.
8. Confirm import summary shows created/updated/skipped/error counts clearly.
9. Open `/advertising`.
10. Confirm imported campaigns appear.
11. Confirm source badge says manual/import.
12. Confirm Spend / Messages / Leads / Orders / Revenue values.
13. Confirm ROAS / CPA / CPL / ROI values.
14. Open Dashboard.
15. Select matching period.
16. Confirm advertising summary matches imported data.
17. Open Analytics.
18. Confirm advertising report matches imported data.
19. Confirm zero denominator rows show `—`.
20. Confirm no `NaN`, `Infinity`, `undefined`, or raw `null` appears.
21. Confirm mobile layout at 375px.
22. Confirm dark/light themes are readable.

## Expected synthetic values

| Campaign | Spend | Messages | Leads | Orders | Revenue | Net Profit | Expected ROAS | Expected CPA | Expected CPL |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DEMO Meta Campaign — Watches | 1000 | 50 | 20 | 5 | 5000 | 1500 | 5.0 | 200 | 50 |
| DEMO Instagram Campaign — Rings | 750 | 35 | 15 | 3 | 2700 | 800 | 3.6 | 250 | 50 |
| DEMO Retargeting Campaign | 500 | 20 | 8 | 2 | 1800 | 450 | 3.6 | 250 | 62.5 |
| DEMO Zero Leads Campaign | 250 | 12 | 0 | 0 | 0 | 0 | 0 | — | — |

## Security checks

- No real Meta token is requested.
- No real ad account ID or business ID is requested.
- No real campaign export is used.
- No private customer/order data is used.
- No screenshots with real ad data are attached to QA artifacts.

## Sprint 4.2.1 CSV Template Validation Status

- Binary `.xlsx` advertising templates are not committed; the pilot template is CSV-only in tracked files.
- Validate the blocker fix with `git ls-files '*.xlsx' 'docs/templates/*' 'frontend/public/templates/*'` and confirm only the two CSV template paths are returned.
- Validate stale links with `rg -n "advertising-import-template\.xlsx|Двійкові|binary files|binary file" docs frontend backend --glob '!node_modules' --glob '!.next' || true`; no user-facing XLSX template link should remain.
- Backend validation for Sprint 4.2.1 must include `compileall`, full `pytest`, and FastAPI app import because Import Center CSV parsing now runs through the backend parser/upload path.
- Frontend validation must include `typecheck`, production build, advertising/import regression scripts, and CSV template link checks for `/advertising` and `/settings/import`.
- Browser-based staging CSV import QA is still required in the deployed staging environment; do not claim manual staging approval until the 21-step flow above is completed with synthetic data.

## Sprint 4.2.2 Manual Staging QA Status

- Staging access was not available in this environment: no deployed staging frontend URL, backend URL, login credentials, or controlled QA workspace were provided to execute browser-based import QA.
- Manual CSV import dry-run, execute import, duplicate import behavior, `/advertising`, Dashboard, Analytics, mobile, and theme checks are therefore **blocked**, not approved.
- Local CI-style validation passed for CSV templates, backend tests, frontend typecheck/build, and advertising/import regression scripts, but this does not replace deployed browser staging QA.
- Pilot readiness decision: advertising import is **not pilot-ready yet** until the 21-step manual staging flow above is completed with synthetic data in the deployed staging environment.
- Next action: provide staging frontend/backend access, a test user with Import Center/Advertising/Dashboard/Analytics permissions, and a controlled synthetic QA workspace; then rerun the manual flow without real ad exports or private customer/order data.
