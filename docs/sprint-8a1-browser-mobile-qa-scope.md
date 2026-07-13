# Sprint 8A.1 Browser/Mobile QA Scope

Temporary QA-only branch. Do not merge.

The Playwright runner verifies staging at:

- 1366 × 768
- 375 × 812
- 390 × 844
- 430 × 932
- 768 × 1024

Scenarios:

- Login
- Dashboard
- Workspace switch
- Leads
- Customers
- Products
- Inventory
- Orders
- Shipment draft page
- Finance
- Advertising
- Analytics
- Settings
- Team
- Logout

Checks:

- no runtime exception
- no refresh-token loop
- no core 404/500
- no CORS/request failure
- no stale Workspace A headers after switching to Workspace B when a second membership is available
- no token/password/API key in sanitized artifacts
