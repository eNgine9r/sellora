# Meta No-write Pilot Preview — Sprint 6D

Sprint 6D adds live read-only client foundation and staging validation gate only.

Meta Ads API is not sync-active.

No scheduled sync jobs, no apply-sync, no ad_metrics writes, no ad_campaigns writes, no customer/order data transfer, and no Conversions API were implemented.

Manual/CSV remains the active Advertising source.

Advertising remains feature-frozen and not pilot-ready.

Real staging OAuth validation, runtime migration QA, Meta App setup, legal review, and browser/mobile QA are still required before pilot-ready claims.

## Preview wording

All sync preview paths must use no-write language: “This is a no-write preview. No Meta data has been imported into Sellora.”

The preview may show what Sellora would be able to read in the future, but it must not create campaigns, update manual/CSV campaigns, write ad metrics, schedule jobs, or send customer/order data to Meta.
