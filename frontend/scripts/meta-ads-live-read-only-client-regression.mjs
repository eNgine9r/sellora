import fs from 'node:fs';

const read = (path) => fs.readFileSync(path, 'utf8');
const assertIncludes = (content, needle, label) => {
  if (!content.includes(needle)) throw new Error(`${label}: missing ${needle}`);
};
const assertNotIncludes = (content, needle, label) => {
  if (content.includes(needle)) throw new Error(`${label}: forbidden ${needle}`);
};

const config = read('backend/app/core/config.py');
const api = read('backend/app/api/v1/meta_ads.py');
const liveClient = read('backend/app/integrations/meta_ads/live_read_only_client.py');
const validationService = read('backend/app/services/meta_ads_staging_validation_service.py');
const validationSchemas = read('backend/app/schemas/meta_ads_staging_validation.py');
const stagingTests = read('backend/tests/test_meta_ads_staging_validation.py');
const liveTests = read('backend/tests/test_meta_ads_live_read_only_client.py');
const docs = [
  'README.md',
  'docs/meta-live-read-only-client.md',
  'docs/meta-staging-validation-gate.md',
  'docs/meta-no-write-pilot-preview.md',
  'docs/advertising-known-blockers.md',
  'docs/known-limitations.md',
  'docs/mvp-readiness.md',
].map(read).join('\n');

assertIncludes(config, 'META_STAGING_VALIDATION_ENABLED', 'staging validation gate config');
assertIncludes(config, 'default=False, alias="META_STAGING_VALIDATION_ENABLED"', 'staging validation disabled by default');

assertIncludes(liveClient, 'class LiveMetaAdsReadOnlyClient', 'live read-only client');
assertIncludes(liveClient, 'def list_ad_accounts', 'account read method');
assertIncludes(liveClient, 'def list_campaigns', 'campaign read method');
assertIncludes(liveClient, 'def get_campaign_insights_preview', 'insights read method');
assertNotIncludes(liveClient, 'def create_campaign', 'no write methods');
assertNotIncludes(liveClient, 'def update_campaign', 'no write methods');
assertNotIncludes(liveClient, 'def delete_campaign', 'no write methods');
assertIncludes(liveClient, 'PERMISSION_MISSING', 'safe error categories');
assertIncludes(liveClient, 'TOKEN_EXPIRED', 'safe error categories');
assertIncludes(liveClient, 'RATE_LIMITED', 'safe error categories');
assertIncludes(liveClient, 'NETWORK_ERROR', 'safe error categories');

assertIncludes(api, '/staging/validate-read-only', 'staging validation route');
assertIncludes(api, 'require_min_role(RoleName.OWNER)', 'OWNER-only validation');
assertIncludes(validationService, 'MetaAdsStagingValidationService', 'staging validation service');
assertIncludes(validationService, 'meta_staging_validation_enabled', 'staging validation gate enforcement');
assertIncludes(validationService, 'writes_performed=False', 'no writes performed');
assertIncludes(validationService, 'sync_active=False', 'sync inactive');
assertIncludes(validationService, 'FakeMetaAdsReadOnlyClient', 'fake client test-safe default');
assertNotIncludes(validationService, '.commit(', 'no ad_campaigns DB writes');
assertNotIncludes(validationService, '.flush(', 'no ad_metrics DB writes');
assertIncludes(validationSchemas, 'writes_performed: bool = False', 'safe validation DTO');
assertIncludes(validationSchemas, 'sync_active: bool = False', 'safe validation DTO');

assertIncludes(stagingTests, 'RoleName.MANAGER', 'MANAGER denial tests');
assertIncludes(stagingTests, 'RoleName.ANALYST', 'ANALYST denial tests');
assertIncludes(stagingTests, 'FakeMetaAdsReadOnlyClient', 'fake client in tests');
assertIncludes(liveTests, 'not hasattr(client, "create_campaign")', 'live client no write method test');
assertIncludes(liveTests, 'MetaReadOnlyErrorCode.PERMISSION_MISSING', 'permission mapping test');
assertIncludes(liveTests, 'MetaReadOnlyErrorCode.TOKEN_EXPIRED', 'token expired mapping test');
assertIncludes(liveTests, 'MetaReadOnlyErrorCode.RATE_LIMITED', 'rate limit mapping test');
assertIncludes(liveTests, 'MetaReadOnlyErrorCode.NETWORK_ERROR', 'network mapping test');

assertNotIncludes(api, 'apply-sync', 'no apply-sync route');
assertNotIncludes(api, 'conversions', 'no Conversions API route');
assertNotIncludes(validationService, 'customer', 'no customer data transfer');
assertIncludes(docs, 'Meta Ads API is not sync-active.', 'not sync-active documentation');
assertIncludes(docs, 'Advertising remains feature-frozen and not pilot-ready.', 'not pilot-ready documentation');
assertIncludes(docs, 'No scheduled sync jobs, no apply-sync, no ad_metrics writes, no ad_campaigns writes, no customer/order data transfer, and no Conversions API were implemented.', 'no-write documentation');

console.log('meta-ads-live-read-only-client-regression passed');
