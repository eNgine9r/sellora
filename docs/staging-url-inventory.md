# Staging URL Inventory — Sprint 6A.1

Meta Ads API is not active.

Sprint 6A.1 documents staging OAuth prerequisites with placeholders only. Do not include secrets, DATABASE_URL values, access tokens, private Render/Supabase credentials, or private workspace IDs in this document.

## URL placeholders

| Input | Placeholder |
| --- | --- |
| `frontend_staging_url` | `https://<frontend-staging-domain>` |
| `backend_staging_url` | `https://<backend-staging-domain>` |
| `api_base_url` | `https://<backend-staging-domain>/api/v1` |
| `oauth_redirect_uri` | `https://<backend-staging-domain>/api/v1/integrations/meta-ads/oauth/callback` |
| `legal_privacy_url` | `https://<frontend-staging-domain>/legal/privacy` |
| `legal_terms_url` | `https://<frontend-staging-domain>/legal/terms` |
| `legal_data_deletion_url` | `https://<frontend-staging-domain>/legal/data-deletion` |
| `allowed_cors_origins` | `https://<frontend-staging-domain>` |
| `meta_app_domain` | `<frontend-staging-domain>` |

## Staging readiness checklist

- [ ] Frontend staging opens.
- [ ] Backend `/docs` or `/health` opens.
- [ ] Frontend can call backend.
- [ ] Login works.
- [ ] CORS allows frontend origin.
- [ ] OAuth redirect URI matches frontend/backend plan.
- [ ] Legal URLs are publicly reachable.
- [ ] No private staging credentials are committed to code, docs, tests, screenshots, or PR text.
