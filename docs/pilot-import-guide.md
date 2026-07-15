# Pilot Import Guide — Sprint 8C

1. Open **Налаштування → Імпорт** in the correct workspace.
2. Choose the import type/preset and download the matching template.
3. Fill the template with synthetic QA data or approved pilot data outside Git.
4. Upload `.xlsx` or `.csv` (maximum 10 MB / 5,000 rows).
5. Select the sheet and preview rows.
6. Review suggested mapping and fix any ambiguous fields.
7. Run validation and dry-run. Import is disabled until a dry-run succeeds for the same file, sheet, type, mapping, duplicate policy, and workspace.
8. Review counts: ready to create, ready to update, skipped, errors.
9. Execute only when the report has no blocking errors.
10. Open the target module and confirm counts/relationships.
11. Rerun the same file to verify duplicate behavior before using larger pilot data.

Do not import real customer files into staging unless the workspace, account, and data handling process are approved for pilot use. Do not use Meta Ads live sync or Nova Poshta TTN creation during import QA.
