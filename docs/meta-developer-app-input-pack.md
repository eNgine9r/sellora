# Meta Developer App Input Pack — Sprint 6A.1

Meta Ads API is not active.

This fill-in pack is for product owner/developer preparation only. No live OAuth, no token storage, no live API calls, and no production sync were implemented.

Do not add real credentials, real app secret, real client secret, real ad account ID, or real token.

## Fill-in inputs

| Field | Placeholder / owner input |
| --- | --- |
| Meta App name | `<Sellora app name>` |
| App type / use case | `<confirm against current Meta requirements>` |
| Business Portfolio / Business Manager | `<business portfolio placeholder>` |
| App domain | `<frontend production or staging domain>` |
| Privacy Policy URL | `https://<frontend-domain>/legal/privacy` |
| Terms URL | `https://<frontend-domain>/legal/terms` |
| Data Deletion URL | `https://<frontend-domain>/legal/data-deletion` |
| OAuth Redirect URI | `https://<backend-domain>/api/v1/integrations/meta-ads/oauth/callback` |
| Contact email | `<support/contact email>` |
| Test user | `<Meta test user placeholder>` |
| Test workspace | `<Sellora synthetic workspace placeholder>` |
| Test ad account / test business | `<Meta test business/ad account placeholder>` |
| Requested permissions | `ads_read` first; `ads_management` / `business_management` only if officially required |
| App Review notes | `<screencast, least-privilege rationale, privacy notes>` |
| Screencast/demo notes | `<synthetic workspace and read-only insights path>` |

## Submission guardrails

- Use synthetic workspace data for demos.
- Do not include customer/order payloads in the Meta review screencast.
- Do not claim Advertising is pilot-ready.
- Do not claim Meta Ads API is active until live OAuth, encrypted token storage, read-only sync, staging QA, workspace isolation QA, and safety scans pass.
