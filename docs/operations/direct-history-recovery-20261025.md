# Direct history recovery — 25 October 2026

## Observed runtime state
The owner workspace's latest history job reported PARTIAL: 100 discovered
conversations, 96 synchronized, 1,349 imported messages, four errors, and last
error META_HISTORY_ACCESS_DENIED. The job did not retain per-conversation provider
codes, so the exact historical cause of all four errors cannot be established
from the saved record alone. Live webhooks and the owner's control message work.

## Reproduced importer defect
MetaInstagramHistoryClient already parses inline message details returned by a
conversation edge. InstagramHistorySyncService discarded these details and
always fetched the message again by ID. If that standalone lookup was rejected,
an otherwise accessible historical message caused a PARTIAL conversation.

Use the inline details when present; retain the existing standalone lookup when
Meta only returns a summary. No API contracts, permissions, tenant filtering,
message identifiers, unread counts, delivery logic or schema changes.

## Verification
- Existing history service/client baseline: 6 passed.
- New text and attachment regressions: both failed with PARTIAL before the fix.
- Instagram integration suite after fix: 62 passed.
- Complete isolated/offline backend suite: 642 passed, 19 PostgreSQL-only skips.
- Regression verifies no standalone lookup for rich inline data, attachment
  preservation, workspace association and repeat-import deduplication.
- Live read-only provider diagnosis and controlled rerun are tracked in the
  private operation checkpoint; do not infer historical causation from rerun success.

## Release
Deploy only after required CI and candidate health checks. Retain the previous
immutable ARM64 image, private environment selector and Direct/Ads credentials.
No outbound messages or real carrier documents are needed for this recovery.
