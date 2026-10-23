# Meta Ads daily USD/UAH import

USD advertising accounts can be selected in a UAH workspace. Same-currency accounts keep a rate of 1; all other cross-currency pairs remain blocked.

For each campaign/day, the importer stores original spend/currency, the workspace spend/currency, the NBU rate, its effective date and source. Conversion uses Decimal and ROUND_HALF_UP to two decimal places. NBU rates use the advertising account's daily date, not the sync date. They are fetched in one bounded request outside DB locks. Missing, malformed or inconsistent rates abort the entire import; no fallback to today's rate is allowed.

The official range API is documented at https://bank.gov.ua/admin_uploads/article/Instr_API_KURS_VAL_data.pdf . `META_ADS_NBU_RATES_URL` defaults to the official endpoint in application configuration. No Meta credentials are sent to NBU.

Migration 202610230045 adds nullable evidence fields to ad_metrics, with no backfill and no changes to existing manual/CSV money. Existing campaign/day identities, workspace locks, reconnect generation checks and manual/CSV conflict protection are retained. Provider-controlled daily fields remain read-only; CRM leads/orders/revenue edits retain FX evidence. Reach and CRM attribution are not imported.

## Source and release lineage

The live OAuth/reader/sync prerequisite was present on the Raspberry release but absent from main's service files, despite migration 039 already being on main. This change brings that deployed prerequisite and its existing tests back into the repository before extending currency support. OAuth credentials remain separate from Instagram credentials.

The Raspberry release is an eight-file overlay over the current timezone-patched image, preserving the existing runtime health, Direct, finance and attribution patches. Do not replace it with an unverified full main build. Take a verified encrypted DB backup, apply migration 045, then deploy the matching image. The prior image can run with the additive nullable columns if application rollback is needed; do not drop FX evidence as part of routine rollback.

Frontend changes show the NBU policy, original currency evidence and accurate source descriptions. The Vercel frontend base was verified against main commit cabf2e2; backend files in this PR do not change the Vercel frontend build.

## Validation

- Arm64, non-root, read-only candidate image: 58 targeted tests passed against a disposable PostgreSQL database, including daily rates, rollback on missing rates, concurrent/idempotent sync, workspace isolation and protected CRM values.
- Migration 044 -> 045 -> 044 -> 045 verified in the disposable database.
- Wider Meta source suite: 133 tests passed after restoring the prerequisite's test contracts (synthetic previews cannot substitute for live data).
- Controlled owner live import and repeat import completed. Repeat import created no campaigns or metrics. Every persisted original/currency/rate/day and converted spend reconciled with the provider daily rows. Existing manual metrics were compared before/after and remained unchanged.

Feature gates remain off by default in source. Runtime activation is an operator action after explicit owner consent. No campaign writes, budget changes, scheduled sync or App Review submission are introduced.
