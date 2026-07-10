# Sprint Dd.2 QA — Landing, Login & Public UI

## Pre-implementation audit

- Public routes found: `/` via `frontend/src/app/page.tsx` and `/login` via `frontend/src/app/login/page.tsx`.
- Existing landing implementation was `frontend/src/components/landing.tsx` with staging/internal copy and raw marketing styles.
- Existing login reused `useAuth().login`, redirected authenticated users to `/dashboard`, and did not prefill credentials.
- Real public legal routes exist: `/legal/privacy`, `/legal/terms`, and `/legal/data-deletion`.
- No registration route, forgot-password route, or beta request route exists in `frontend/src/app`; public CTA therefore uses `/login` only.
- Existing brand assets are available under `frontend/public/brand` and `frontend/public/branding`.
- Localization dictionaries exist for Ukrainian and English at `frontend/src/i18n/messages/uk.json` and `frontend/src/i18n/messages/en.json`.

## Routes and CTA decisions

| Item | Decision |
| --- | --- |
| Primary public CTA | `/login` with “Увійти в Sellora” / “Log in to Sellora”. |
| Secondary landing CTA | Scrolls to the workflow section on the current page. |
| Registration | Omitted because no real route/flow exists. |
| Forgot password | Omitted because no real route/flow exists. |
| Beta request | Omitted because no real route/flow exists. |
| Legal links | Keep only real privacy, terms, and data deletion routes. |

## Public route validation

| Check | Result | Notes |
| --- | --- | --- |
| `/` renders logged out | Automated build passed; browser QA pending | Requires browser runtime for visual confirmation. |
| `/login` renders logged out | Automated build passed; browser QA pending | Requires browser runtime for visual confirmation. |
| Login submit uses existing auth flow | Passed by code review and auth/API regression | Submit still calls `useAuth().login`. |
| Invalid credentials safe message | Implemented | Message does not reveal whether email exists. |
| Session restore/authenticated redirect | Preserved | Auth provider and redirect behavior unchanged. |
| Language switching | Implemented with existing `LanguageSwitcher` | Browser interaction pending. |
| Mobile menu | Implemented with keyboard/ESC handling | Browser interaction pending. |
| Legal links | Implemented only for existing routes | `/legal/privacy`, `/legal/terms`, `/legal/data-deletion`. |
| Horizontal body scroll | Static CSS and layout guard present | Viewport measurement pending. |

## Viewport matrix

Browser visual QA was not available in this container. These viewports remain pending for manual or automated browser verification:

- 1280×800
- 1366×768
- 1440×900
- 1536×1024
- 1920×1080
- 1024×768
- 768×1024
- 430×932
- 390×844
- 375×812

## Automated validation results

- `npm run typecheck` — passed.
- `npm run build` — passed.
- `npm run lint` — passed with existing non-blocking warnings outside the Dd.2 public-page scope.
- `node frontend/scripts/localization-regression.mjs` — passed.
- `node frontend/scripts/auth-api-boundary-regression.mjs` — passed.
- `node frontend/scripts/mobile-ux-pwa-mvp-regression.mjs` — passed.
- `git diff --check` — passed.

## Manual QA still required

- Visual verification of landing and login at all required viewports.
- Login with a valid account and invalid credentials against a real backend.
- Verify no console errors in browser.
- Verify focus trap and focus return in the public mobile menu.
- Verify no horizontal body scroll by measuring `document.documentElement.scrollWidth <= window.innerWidth`.

## Sprint Dd.2.1 regression follow-up

Dd.2.1 fixed the confirmed public UI regressions from manual QA: duplicate login-equivalent header CTAs, inconsistent header control sizing, English indicator localization, mobile demo preview overflow, and mobile login content order.

Final browser verification for light/dark themes and the requested viewport matrix remains required outside this container.

## Final status

Final status: APPROVED based on completed user browser verification before Sprint Dd.3.
