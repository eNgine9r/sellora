# Sellora Synthetic Demo Dataset

Sprint 2.6 adds `backend/scripts_seed_demo.py` as a safe, synthetic, idempotent demo dataset generator. It creates a demo workspace using stable DEMO identifiers and does not contain real customer, order, product, advertising, or private store data.

## Run locally

```bash
cd backend
python scripts_seed_demo.py
```

The script uses the configured application database connection and creates or reuses the workspace slug `sellora-demo`.

## Included synthetic data

- DEMO products across rings, necklaces, earrings, and watches.
- DEMO variants with stable SKUs such as `DEMO-RING-LUNA-GOLD`.
- Inventory examples with healthy, low-stock, incoming, and out-of-stock states.
- DEMO customers and converted leads with synthetic Instagram handles.
- Historical multi-status orders with captured item prices/costs.
- Shipments with synthetic tracking numbers.
- One Instagram advertising campaign with 14 days of manual metrics.

## Idempotency

The script checks stable workspace slug, product SKU, variant SKU, Instagram username, order number, campaign name, metric date, and shipment order before creating records. Running it repeatedly should not duplicate DEMO records.

## Analytics verification after seeding

After running the demo seed, verify:

- Dashboard revenue and order count are non-zero.
- Sales report has daily rows and revenue.
- Product report shows top products/categories from captured order items.
- Advertising report shows spend, revenue, ROAS, CPA, and CPL.
- Customer report shows repeat/customer spend values.
- Inventory report shows low/out-of-stock examples.
- Business insights show deterministic inventory or advertising warnings where applicable.

## Sprint 2.7 demo QA

After seeding, the frontend should identify the demo workspace with a localized notice and a setup checklist. Verify that `/dashboard`, `/analytics`, `/orders`, `/products`, `/inventory`, `/customers`, `/leads`, `/shipments`, `/advertising`, and `/settings/import` show meaningful synthetic data or clear next actions.
