# SA.2 → SA.3 — handoff

Platform Admin UI lives at `/platform-admin`. The screen uses the merged SA.1 backend from [PR #413](https://github.com/eNgine9r/sellora/pull/413). It checks `/me` before fetching platform data and uses the existing cookie-session sign-in, i18n and UI components.

- Dashboard values come from `GET /api/v1/platform-admin/summary` and show the snapshot timestamp. An enabled workspace is a registry setting. Product activity has its own definition and data source in SA.3.
- The directory uses backend search, active and demo filters, and cursor pagination. The workspace profile uses the detail endpoint for the plan, status, UTC term and active membership count.
- The transport omits the workspace header and bypasses shared caching. Query keys contain the operator ID. Directory access requires the backend capability and the screen withholds data on denial.
- Browser coverage uses the real API and synthetic fixtures in disposable PostgreSQL. Desktop and mobile projects cover sign-in, a tenant OWNER denial, KPI values, search, pagination, drawer focus, and error recovery.

Start SA.3 after this frontend PR is merged and a separate SA.3 task is opened. Extend the authorized frontend with product activity when its server-side events and read API are available. See [status](../STATUS.md) and [roadmap](../ROADMAP.md).
