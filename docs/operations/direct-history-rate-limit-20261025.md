# Direct history throttling recovery — 25 October 2026

## Reproduced live cause
The first controlled rerun after #338 imported 213 messages and created seven
leads through the existing history workflow. It preserved one control message,
created zero provider-ID duplicates, and left customers, orders and shipments
unchanged. Its last page ended PARTIAL (95/100, five generic access errors).

A bounded read-only diagnosis of those tail conversations reproduced HTTP 403,
Graph code 4, subcode 1349210, is_transient=true, "Application request limit
reached" specifically on message cursor requests. The client recognized only
HTTP 429 as throttling, so the worker skipped these temporary failures as access
errors. The original four errors did not retain their provider codes; do not
claim their exact historical cause is proven.

## Repair
- Recognize Graph application-limit code 4 even with HTTP 400/403. Preserve real
  authorization errors and the existing HTTP 429 mapping; never log tokens or
  provider request URLs.
- On a temporary failure, retain the previous conversation page checkpoint and
  rewind that page's conversation counters. Preserve unrelated permanent errors. Already saved
  messages remain durable and are deduplicated when that page is replayed.
- Keep transient throttling separate from permanently failed conversations, so
  a successful retry can finish COMPLETED.
- Back off by throttle occurrences, not the count of successful pages. The first
  limit waits two minutes; subsequent limits increase the delay up to 32 minutes.
- The production worker uses InstagramHistorySyncVisibilityService. Its duplicated
  process_next implementation is removed in favor of the shared checkpoint loop;
  its visible-dialog accounting remains in a small counting hook. The inline
  identity/media hydration helper is also shared with the base service.
- The same replay, media and error regressions run against both the base service
  and the actual class imported by runtime_worker. Six production-path regressions
  reproduced the override defect before consolidation.
- Existing workspace isolation, RBAC, credentials, schema and outbound flags are
  unchanged. No repeated manual resync is needed while RETRY_PENDING is active.

## Tests
New HTTP-code and interrupted-last-page regressions failed before the fix.
Full isolated backend validation: 665 passed, 19 PostgreSQL-dependent skips.
Tests cover text/int provider code 4 on 400/403, genuine authorization errors,
page replay at the conversation limit, durable-message deduplication, recovery
completion, preservation of unrelated permanent errors, and the first retry
delay after nine successful page attempts.

## References
- https://developers.facebook.com/docs/graph-api/overview/rate-limiting/
- https://developers.facebook.com/docs/graph-api/guides/error-handling/

## Operations
Deploy only after CI and candidate checks; retain the #338 immutable image and
private selector. A successful software release is not proof that Meta has
lifted its rate limit. Record actual job status and next_retry_at in the private
release checkpoint, and do not claim the whole archive was synchronized.
