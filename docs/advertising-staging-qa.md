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
