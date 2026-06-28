# Sprint 1.8 – Advertising & ROAS Engine

Sprint 1.8 adds manual advertising tracking without connecting to Meta Ads, Instagram Graph, Nova Poshta, or AI services.

## Backend scope

- `AdCampaign` stores workspace-scoped manual campaign metadata: platform, status, objective, budgets, date range, and notes.
- `AdMetric` stores one workspace-scoped daily metrics row per campaign/date.
- Advertising analytics are computed from `AdMetric` rows and expose CPA, CPL, CPC, CPM, CTR, ROAS, and ROI.
- OWNER can create/update/delete campaigns and metrics.
- OWNER and ANALYST can read sensitive profit metrics.
- MANAGER can read basic performance metrics, but `net_profit` and `roi` are omitted.

## Import Center integration

The Import Center supports `ad_campaigns` and `ad_metrics` as manual mapped entity types. This remains a user-confirmed import flow and uses aliases only; no private spreadsheet rows are stored in docs, tests, migrations, or seed data.

## API routes

- `GET /api/v1/advertising/campaigns`
- `POST /api/v1/advertising/campaigns`
- `GET /api/v1/advertising/campaigns/{campaign_id}`
- `PUT /api/v1/advertising/campaigns/{campaign_id}`
- `DELETE /api/v1/advertising/campaigns/{campaign_id}`
- `GET /api/v1/advertising/metrics`
- `POST /api/v1/advertising/metrics`
- `GET /api/v1/advertising/campaigns/{campaign_id}/metrics`
- `DELETE /api/v1/advertising/metrics/{metric_id}`
- `GET /api/v1/advertising/summary`
- `GET /api/v1/advertising/campaign-performance`
- `GET /api/v1/advertising/trend`
