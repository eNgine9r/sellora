# Sprint 1.8.1 – Staging UX & Auth Stabilization

Sprint 1.8.1 stabilizes the staging frontend experience without changing the deployment architecture.

## Frontend auth flow

1. `/login` accepts email and password.
2. Successful login stores the token pair through a centralized auth service.
3. The auth provider calls `/auth/me` and stores the current user.
4. The first available workspace membership is selected automatically.
5. The API client attaches the active session and `X-Workspace-ID` headers automatically.
6. Protected pages redirect unauthenticated users to `/login`.
7. The app shell displays navigation, workspace name, workspace switcher, user email, and logout.

## Protected routes

- `/overview`
- `/leads`
- `/customers`
- `/products`
- `/inventory`
- `/orders`
- `/analytics`
- `/advertising`
- `/settings/import`

## Security notes

- Tokens are not displayed in the UI.
- Workspace IDs are not entered manually in normal staging screens.
- API base URL comes from `NEXT_PUBLIC_API_BASE_URL` with local development fallback only.
- Staging architecture remains Vercel frontend, Render backend, and Supabase PostgreSQL.
- Shipments, Nova Poshta API, Meta Ads API, and AI Insights were not added.
