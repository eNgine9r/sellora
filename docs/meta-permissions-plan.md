# Meta Permissions Plan — Sprint 6A

Meta Ads API is not active.

Sprint 6A documents the permission strategy only. No live OAuth, no token storage, no live API calls, and no production sync were implemented.

## Permission strategy

### Phase 1 — read-only insights

Request the minimum permission needed to read advertising delivery and spend data for owner-facing reports. The initial expected permission to verify against official Meta documentation is `ads_read`.

Supported user-facing feature: read-only advertising insights sync into Sellora preview/reporting after token storage and staging QA are implemented in later sprints.

### Phase 2 — management/write actions

Only consider broader permissions if Sellora later needs to create, edit, or manage campaigns. `ads_management` must not be requested for a read-only MVP unless official Meta requirements make it necessary for the approved access path.

Supported user-facing feature if ever approved: campaign management workflows. This is out of scope for Sprint 6A and not part of the current MVP.

### Phase 3 — Conversions API

Conversions API remains a separate future privacy/legal sprint. It must not be bundled with read-only Marketing API work because it may involve customer event data, consent, hashing, and legal review.

## Permissions to verify before implementation

| Permission | Initial position | Why it may be needed | App Review evidence | Explicit limits |
| --- | --- | --- | --- | --- |
| `ads_read` | Preferred read-only candidate | Read advertising account delivery and insights data | Screencast showing owner connects account and views read-only metrics | No campaign writes, no customer data sent to Meta |
| `ads_management` | Future/conditional only | May be required by some Marketing API access paths or future campaign management | Evidence only if write/manage scope is approved | Not requested for read-only MVP unless official docs require it |
| `business_management` | Conditional only | May be needed for Business Portfolio asset workflows | Business asset selection and permission rationale | Not requested unless asset access cannot work without it |

## Rules

- Do not over-request permissions.
- Do not request write permissions for the read-only MVP unless official Meta requirements make them unavoidable.
- Document why each permission is needed before implementation.
- Document the user-facing feature supported by each permission.
- Document App Review evidence before requesting production access.
- Explicitly do not request Conversions API permissions in Part 6 read-only sync.

## Official references to re-check

- Meta permissions reference: https://developers.facebook.com/docs/permissions/
- Marketing API authorization guide: https://developers.facebook.com/documentation/ads-commerce/marketing-api/get-started/authorization
