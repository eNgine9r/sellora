# Sellora Staging QA Checklist

Use this checklist for manual staging smoke testing before accepting MVP changes. Keep all credentials, tokens, workspace identifiers, private customer data, and screenshots with sensitive information out of issues, docs, logs, and pull request comments.

## Auth

- Open the public landing page at `/` and verify it does not redirect to login.
- Open `/login`, sign in with a staging test account, and confirm the app redirects to `/dashboard`.
- Reload `/dashboard` and confirm the session restores without asking for a token or workspace ID.
- Let the access token expire during a staging session, reload the page, and confirm refresh-token recovery keeps the user signed in when refresh is valid.
- Use Log out and confirm the session is cleared and private routes redirect to `/login`.

## CRM

- Create a lead with synthetic test data.
- Convert a lead to a customer.
- Add a customer note.
- Add a customer tag.
- Add a customer address.

## Catalog

- Create a product.
- Create a product variant.
- Verify inventory is created for the variant.
- Perform a stock-in transaction.
- Verify low-stock indicators appear when stock is below the configured minimum.

## Orders

- Create an order with synthetic products and customer data.
- Verify inventory reservation occurs.
- Move the order to shipped.
- Complete the order.
- Cancel a separate test order.
- Return a separate test order and verify inventory restoration through the order workflow.

## Advertising

- Create a campaign with synthetic data.
- Add daily metrics.
- Verify CPA and ROAS calculations.
- Verify manager users cannot see net profit or ROI values.

## Shipments

- Create a shipment linked to a test order.
- Mark the shipment in transit and verify the order status updates correctly.
- Mark a shipment delivered and verify the order status updates correctly.
- Mark a shipment returned and verify the order status and inventory behavior follow the order return workflow.

## Import Center

- Upload an Excel file with synthetic staging data only.
- Run mapping suggestions.
- Preview the mapped rows.
- Run a dry run.
- Review validation issues and the import report.
- Execute the import only when the report is acceptable.

## Mobile

- Check `/login`, `/dashboard`, `/leads`, `/customers`, `/orders`, `/products`, `/inventory`, `/shipments`, `/advertising`, `/analytics`, and `/settings/import` at mobile width.
- Verify the sidebar opens as a drawer and closes cleanly.
- Verify cards stack vertically without horizontal page overflow.
- Verify tables either become cards or stay inside controlled horizontal scroll containers.
- Verify forms and dialogs fit phone screens and primary buttons remain touch-friendly.

## Real Product Catalog Import QA

1. Login.
2. Open `/settings/import`.
3. Upload a private product catalog template from local storage.
4. Select `your_jewelry_product_catalog_v1`.
5. Click Suggest mapping.
6. Preview rows.
7. Run dry-run.
8. Review product, variant, inventory, and image counts.
9. Review sample warnings and errors.
10. Import a small private test subset first when possible.
11. Verify `/products`.
12. Verify variants are available in selects.
13. Verify `/inventory`.
14. Create a test order from an imported variant.
15. Verify dashboard still loads.
16. Confirm no private business data is exposed in UI, docs, logs, screenshots, or tests.

## MVP Edit Flow QA

- Edit a lead name/status/notes and confirm the list refreshes.
- Edit a customer name/phone/city and confirm customer details still load.
- Edit a product SKU/name/category/brand/status and confirm variants and inventory are preserved.
- Edit a product variant SKU/color/size/price/barcode/status and confirm duplicate SKUs are rejected.
- Adjust inventory with a stock transaction, then update incoming and minimum quantity.
- Edit order safe fields only: payment status, costs, and notes; keep status changes through status actions.
- Edit shipment tracking/carrier/recipient/city/warehouse/cost fields; keep status changes through shipment status actions.
- Edit an advertising campaign budget/status/date/notes.
- Edit an advertising metric spend/counts/revenue/profit and confirm duplicate campaign/date is rejected.
- Verify an analyst account cannot perform edit mutations.
- Re-check create flows, Import Center dry-run/import, dashboard loading, and workspace header behavior after edits.
