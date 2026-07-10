# Sprint Dd.2.1 QA — Dual Theme & Public UI Regression Fixes

## Confirmed issues fixed

- Public UI now uses light values in `:root` and dark values in `.dark` for semantic tokens.
- Public Header no longer shows two login-equivalent actions. It shows `Увійти` / `Log in` to `/login` and `Переглянути можливості` / `Explore features` to `#capabilities`.
- Header controls were normalized to 40px on desktop and 44px/full-width behavior in the mobile menu.
- English login indicators now use English copy (`EN — English interface`) instead of Ukrainian copy.
- Mobile landing demo preview was changed to a contained vertical presentation for funnel and stacked recent orders.
- Mobile login now renders the login form before the product context below 1024px.

## Theme audit

Reviewed and updated:

- `frontend/src/app/globals.css`
- `frontend/tailwind.config.ts`
- shared primitives and states
- overlays
- App Shell sidebar/topbar touch points
- public header/footer
- landing/login
- language and theme controls

Brand-locked colors remain only for the Sellora gradient and documented decorative glow. Semantic colors should be preferred for all new UI work.

## Tested routes and viewport plan

Automated build covers:

- `/`
- `/login`
- protected routes included in Next build output

Browser QA remains required for:

- 1280×800
- 1440×900
- 1920×1080
- 768×1024
- 430×932
- 390×844
- 375×812

## Automated validation results

- `npm run typecheck` — passed.
- `npm run build` — passed.
- `npm run lint` — passed with existing non-blocking warnings outside this sprint scope.
- `node frontend/scripts/localization-regression.mjs` — passed.
- `node frontend/scripts/auth-api-boundary-regression.mjs` — passed.
- `node frontend/scripts/mobile-ux-pwa-mvp-regression.mjs` — passed.
- `git diff --check` — passed.

## Remaining limitations

Browser light/dark visual QA was not available in this container, so final approval still requires manual browser verification of the routes, themes, and viewport matrix above.
