## MetaAdsSyncPreviewService.preview_insights in backend/app/services/meta_ads_sync_preview_service.py (L87-L111)

**Purpose:** Produces read-only Meta campaign delivery preview without importing campaign or metric rows.

**Inputs & Assumptions:**
- workspace_id: trusted backend workspace context; Analyst minimum route (`api/v1/meta_ads.py:L88-L97`).
- Dates/account_id: semi-trusted route parameters; dates required and parsed, account optional.
- Client: trusted injection boundary. Default is FakeMetaAdsReadOnlyClient (service L39-L50), not the separately implemented live adapter.
- A preview connection corresponds to live delivery numbers: **nothing found** in the route graph. No route injects live client.

**Outputs & Effects:** Preview DTOs with date, masked campaign ID, campaign name, spend/impressions/clicks/messages; reach forced None (L99-L108). Warnings explicitly state no import/no writes (L24-L25). No persistence or ad/customer mutation.

**Block-by-Block:**

```python
# L88-L94
readiness = self._readiness(workspace_id)
if not readiness.ready:
    return MetaInsightsPreviewResponse(**self._not_ready_payload(readiness))
if date_from > date_to:
    return MetaInsightsPreviewResponse(ready=False, reason="invalid_date_range", message="Meta Ads preview date range is invalid.")
selected_account_id = account_id or self._default_account_id()
campaigns_by_id = {campaign.external_campaign_id: campaign for campaign in self.client.list_campaigns(selected_account_id)}
```

- **What:** Checks feature/connection gates, date order and selects account.
- **Why here:** Does not call client for not-ready or invalid dates.
- **Assumes:** Injected client limits accounts to authorized context; fake client returns empty for any account except fake_act_001 (`fake_client.py:L28-L30,L62-L64`).
- **Establishes:** _readiness accepts CONNECTED or MOCK_ONLY, token presence for CONNECTED, feature flags on, production sync off (service L113-L128).

```python
# L96-L111 (projection)
for row in self.client.get_campaign_insights_preview(selected_account_id, date_from, date_to):
    campaign = campaigns_by_id.get(row.external_campaign_id)
    # Build safe preview DTO; missing name -> Unknown Meta campaign.
return MetaInsightsPreviewResponse(ready=True, reason=None, message="Meta Ads insights sync preview is available.", insights=insights)
```

- **What:** Converts client records, never writes them.
- **Assumes:** DTO normalization and client handle remote response trust boundary.
- **Establishes:** All returned items include explicit no-write warnings (L108); readiness is availability of this preview path, not proof of production sync.

**Cross-Function Dependencies:**
- _readiness (L113-L128) -> MetaAdsConnectionRepository.get_current (`meta_ads_connection_repository.py:L15-L25`): newest undeleted meta_ads connection scoped by workspace.
- _not_ready_payload (L130-L131): standard not-ready DTO.
- _default_account_id (L133-L135): first client account or empty string.
- FakeMetaAdsReadOnlyClient methods (`read_only_client.py:L27-L40`) forward to FakeMetaAdsClient; that class performs no HTTP, generates deterministic fake campaigns and per-day rows (`fake_client.py:L9-L93`).
- LiveMetaAdsReadOnlyClient exists (`live_read_only_client.py:L49-L155`), but searching backend/app for its name found no construction/runtime injection.
- Staging validation independently defaults fake at `meta_ads_staging_validation_service.py:L81-L87`; response identifies mode (L82,L106).

**Open Questions:**
- Where will real account authorization/selection and token decryption be wired for the live adapter?
- What should preview UI display when mode=fake to prevent misunderstanding? No live provider calls were made by this audit.
