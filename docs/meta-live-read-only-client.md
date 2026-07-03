# Meta Live Read-only Client Foundation — Sprint 6D

Sprint 6D adds live read-only client foundation and staging validation gate only.

Meta Ads API is not sync-active.

No scheduled sync jobs, no apply-sync, no ad_metrics writes, no ad_campaigns writes, no customer/order data transfer, and no Conversions API were implemented.

Manual/CSV remains the active Advertising source.

Advertising remains feature-frozen and not pilot-ready.

Real staging OAuth validation, runtime migration QA, Meta App setup, legal review, and browser/mobile QA are still required before pilot-ready claims.

## Scope

- `LiveMetaAdsReadOnlyClient` exposes read-only account, campaign, and insights-preview methods.
- The live client has no create, update, delete, import, apply, webhook, scheduled sync, or event upload methods.
- Error mapping returns safe internal categories such as `PERMISSION_MISSING`, `TOKEN_EXPIRED`, `TOKEN_INVALID`, `RATE_LIMITED`, `NETWORK_ERROR`, `CONFIG_MISSING`, `MALFORMED_RESPONSE`, and `UNKNOWN_ERROR`.
- Tokens remain server-only and are never returned by preview DTOs.

## Current guardrails

- Live behavior is gated and disabled by default.
- CI and unit tests use fake clients or injected HTTP fakes only.
- The foundation is intended for future controlled staging validation, not production sync.
