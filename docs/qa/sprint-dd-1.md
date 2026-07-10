# Sprint Dd.1 QA Notes

## Automated checks

To be completed in the implementation report after running available scripts:

- `npm run typecheck`
- `npm run build`
- available regression scripts for localization and auth/workspace behavior

## Responsive smoke matrix

Desktop viewports to verify manually or with browser tooling:

- 1280×800
- 1366×768
- 1440×900
- 1536×1024
- 1920×1080

Regression viewports:

- 1024×768
- 768×1024
- 430×932
- 390×844
- 375×812

## Manual QA checklist

- No horizontal body scroll.
- Sidebar and topbar do not overlap content.
- Active sidebar state is dark/purple, not a white pill.
- Mobile bottom navigation remains visible and usable.
- Mobile drawer navigation opens and closes.
- Profile/workspace sheet, workspace switching, login restore, and logout remain functional.
- Drawers/modals close on ESC and keep visible focus states.
- Loading, empty, and error states are readable on the dark canvas.

## Current limitation

Browser visual QA requires an authenticated workspace session and should remain pending unless run against a prepared local or staging account. Do not mark Sprint Dd.1 fully approved without this verification.
