import fs from 'node:fs';

const read = (path) => fs.readFileSync(path, 'utf8');
const check = (name, condition) => ({ name, passed: Boolean(condition) });

const qa = read('docs/sprint-6e-meta-runtime-staging-qa.md');
const gate = read('docs/meta-pilot-readiness-gate.md');
const readme = read('README.md');
const blockers = read('docs/advertising-known-blockers.md');
const limitations = read('docs/known-limitations.md');
const api = read('backend/app/api/v1/meta_ads.py');
const validationSchema = read('backend/app/schemas/meta_ads_staging_validation.py');
const validationService = read('backend/app/services/meta_ads_staging_validation_service.py');
const previewService = read('backend/app/services/meta_ads_sync_preview_service.py');
const migration = read('backend/alembic/versions/202607030018_meta_ad_connections.py');
const docs = `${qa}\n${gate}\n${readme}\n${blockers}\n${limitations}`;
const appCode = `${api}\n${validationSchema}\n${validationService}\n${previewService}`;

const checks = [
  check('Sprint 6E QA report exists', qa.includes('Sprint 6E') && qa.includes('Meta Runtime, Staging OAuth & Pilot Readiness QA')),
  check('meta-pilot-readiness-gate exists', gate.includes('Meta Pilot Readiness Gate') && gate.includes('Final decision: NOT_READY')),
  check('runtime migration QA status documented', qa.includes('PostgreSQL migration QA result') && qa.includes('Status: BLOCKED') && gate.includes('Runtime migration QA')),
  check('OAuth staging validation status documented', qa.includes('OAuth staging validation result') && qa.includes('Real Meta OAuth staging validation was not run')),
  check('RBAC validation status documented', qa.includes('RBAC QA result') && qa.includes('MANAGER and ANALYST cannot')),
  check('no-write validation status documented', qa.includes('No-write validation result') && qa.includes('sync_active=false') && qa.includes('writes_performed=false')),
  check('sync_active=false contract remains', validationSchema.includes('sync_active: bool = False') && validationService.includes('sync_active=False')),
  check('writes_performed=false contract remains', validationSchema.includes('writes_performed: bool = False') && validationService.includes('writes_performed=False')),
  check('no scheduled sync', !/BackgroundTasks|cron|scheduler|scheduled sync active/i.test(appCode)),
  check('no apply-sync', !/apply-sync|apply_sync|applySync/i.test(appCode)),
  check('no Conversions API', !/Conversions API active|customer event upload|send.*customer.*Meta/i.test(appCode)),
  check('no ad_metrics write claim', docs.includes('no ad_metrics writes') && !/AdMetric\(|\.add\(|commit\(/.test(validationService + previewService)),
  check('no ad_campaigns write claim', docs.includes('no ad_campaigns writes') && !/AdCampaign\(|create_campaign|update_campaign/.test(validationService + previewService)),
  check('Meta API not production sync-active', docs.includes('Meta Ads API is not production sync-active') || docs.includes('Meta Ads API is not sync-active')),
  check('Advertising not pilot-ready', docs.includes('Advertising remains feature-frozen and not pilot-ready')),
  check('migration remains latest connection migration', migration.includes('revision: str = "202607030018"') && migration.includes('meta_ad_connections')),
  check('no raw token column', !migration.includes('sa.Column("access_token"') && !migration.includes('sa.Column("refresh_token"')),
  check('no real credential-looking values', !/EA[A-Za-z0-9]{20,}|act_\d{8,}|Authorization: Bearer\s+[A-Za-z0-9._-]+|app_secret\s*[:=]\s*['"][^'"]+/.test(`${docs}\n${appCode}`)),
];

const failed = checks.filter((item) => !item.passed);
if (failed.length) {
  console.error('Meta runtime staging QA regression failed:');
  for (const item of failed) console.error(`- ${item.name}`);
  process.exit(1);
}

console.log(`Meta runtime staging QA regression passed (${checks.length} checks).`);
