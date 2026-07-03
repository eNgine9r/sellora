# Legal URL Readiness — Sprint 6A.1

Meta Ads API is not active.

Sprint 6A.1 prepares legal URLs, staging URL inventory, Meta App input pack, OAuth redirect URI planning, and environment variable planning only.

No live OAuth, no token storage, no live API calls, and no production sync were implemented.

Legal pages are MVP drafts and must be reviewed before production launch, payment activation, or Meta App Review submission.

## Draft public URLs

| Page | Local route | Production URL placeholder | Staging URL placeholder | Status |
| --- | --- | --- | --- | --- |
| Privacy Policy | `/legal/privacy` | `https://<production-frontend-domain>/legal/privacy` | `https://<frontend-staging-domain>/legal/privacy` | Draft / needs legal review |
| Terms of Service | `/legal/terms` | `https://<production-frontend-domain>/legal/terms` | `https://<frontend-staging-domain>/legal/terms` | Draft / needs legal review |
| Data Deletion | `/legal/data-deletion` | `https://<production-frontend-domain>/legal/data-deletion` | `https://<frontend-staging-domain>/legal/data-deletion` | Draft / needs legal review |

## Review ownership

- Product owner: fill legal entity details, support contact, effective date, production domain, and staging domain.
- Qualified lawyer: review privacy, terms, data deletion, Meta App Review wording, payments wording, tax/accounting disclaimers, and data retention limits.
- Engineering: verify routes are publicly reachable and do not expose secrets or private tenant data.

## Before public launch

- Replace all placeholders with approved public values.
- Confirm legal pages are reachable without authentication.
- Confirm no legal page claims lawyer approval until review is actually complete.
- Confirm no real Meta credentials, tokens, ad account IDs, DATABASE_URL values, or private staging credentials are included.
