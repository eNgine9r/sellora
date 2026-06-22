# Meta Ads Privacy and Safety Notes

Sellora must treat advertising integration data as sensitive. Sprint 4.0 only adds the foundation and placeholder messaging; it does not activate automatic Meta Ads API sync.

## Token and credential rules

- Never expose raw Meta access tokens in frontend responses, logs, docs, tests, screenshots, PR text, or browser console output.
- Never commit app secrets, access tokens, business IDs, ad account IDs, customer data, workspace IDs, or private campaign exports.
- Future tokens must be exchanged and refreshed server-side, encrypted at rest, masked in UI, and scoped to one workspace.
- Credential management should be OWNER-only.

## Customer and attribution privacy

- Do not send private Sellora customer/order data to Meta without an explicit future product design, consent review, and privacy review.
- Do not store unnecessary personal data from Meta.
- Attribution should prefer internal campaign identifiers and aggregated metrics before any personal-data workflow is considered.

## API and platform rules

- Use official Meta APIs only.
- Do not scrape Instagram Direct, ad accounts, or private pages.
- Do not provide bypasses for Meta permissions, rate limits, app review, or user consent.
- Automated tests must use fake/mocked Meta clients only and must never call the real Meta API.

## MVP-safe path

Manual advertising import remains the safest MVP path for pilot shops. It allows teams to validate ROAS, CPA, CPL, cost per message, and campaign performance without storing Meta credentials or relying on API availability.

## Sprint 4.0.1 safety validation

Safety scans were rerun after Sprint 4.0 and found only safe source, documentation, and synthetic test references. No real Meta access token, app secret, ad account ID, business ID, campaign export, workspace ID, or private customer/order data was added.
