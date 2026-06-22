# Staging manual QA checklist

Use synthetic records only. Do not paste credentials, tokens, workspace identifiers, private customer data, or request headers into screenshots, tickets, or chat.

## Core creation flow

1. Log in through the normal staging sign-in page.
2. Confirm the app shell finishes loading and shows an active workspace selector value.
3. Open **Leads** and create a lead with only a name.
4. Create another lead with phone, Instagram username, Instagram profile URL, source, expected revenue, and notes.
5. Check a protected Network request and confirm the workspace header contains exactly one UUID value and no comma.
6. Open **Customers** and create a customer with a name and optional contact/location fields.
7. Open **Products** and create a product with only a name.
8. Create another product with SKU, description, and a primary image URL.
9. Create a product variant from the product dialog flow and confirm the product select contains products.
10. Open **Inventory**, select inventory for the new variant, and record a stock-in transaction.
11. Open **Orders**, confirm variants are available, and create an order with a valid item quantity and price.
12. Open **Shipments**, confirm orders are available, and create a draft shipment.
13. Open **Advertising**, create a campaign, then create a daily metric for that campaign.
14. Revisit Dashboard and list pages to confirm new synthetic records are visible.
15. Confirm normal valid submissions do not return 422 responses.
16. If validation is expected, confirm the form displays a safe field-level message instead of a page-load error.

## Safe debugging notes

- Capture only endpoint path, status code, and sanitized validation text.
- Never capture auth headers, tokens, private identifiers, environment values, or raw stack traces.
- If a list endpoint fails, verify the page waited for authentication and workspace readiness before requesting data.
