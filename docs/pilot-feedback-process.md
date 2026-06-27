# Sellora Pilot Feedback Process

This process is for controlled pilot testing with 5–15 Instagram stores. It must stay privacy-safe: do not ask users to paste passwords, API keys, access tokens, private spreadsheets, raw customer lists, full authorization headers, Nova Poshta API keys, or workspace IDs into feedback.

## How pilot users submit feedback

1. Click **Фідбек / Feedback** in the app topbar.
2. Choose a category: `ISSUE`, `IDEA`, `CONFUSION`, `PRAISE`, or `OTHER`.
3. Optionally add a 1–5 rating.
4. Write a short message with what happened, what was expected, and whether the issue blocks work.
5. Keep private customer/order data out of the message.

The app captures the current page path so the team can triage without showing internal workspace IDs in the UI.

## Feedback categories

- `ISSUE` — something is broken or behaves incorrectly.
- `IDEA` — improvement request or product idea.
- `CONFUSION` — user does not understand what to do next.
- `PRAISE` — something works well and should be preserved.
- `OTHER` — anything that does not fit the categories above.

## Severity levels

- **Critical** — blocks login, workspace access, orders, imports, or other core flow.
- **Major** — core feature works incorrectly or strongly confuses the user.
- **Minor** — visual, copy, empty-state, or small UX issue.
- **Improvement** — useful but not blocking pilot success.
- **Question** — expected behavior is unclear or needs user education.

## Triage workflow

1. Review new feedback daily during active pilots.
2. Assign severity and decide whether it is a bug, improvement, limitation, or education issue.
3. Update status: `NEW`, `REVIEWED`, `PLANNED`, `FIXED`, or `WONT_FIX`.
4. Add confirmed limitations to `docs/known-limitations.md`.
5. Group repeated confusion points into onboarding/import copy improvements.
6. Communicate fixes to pilot users in a short release note without mentioning private data.

## Bug vs improvement decision

Treat as a bug if the existing MVP promise fails: login, workspace isolation, product/order/inventory/import/analytics flow, or localized UI. Treat as improvement if the request is valuable but outside the current MVP scope, such as Instagram Direct API, Meta Ads API, billing, AI parser, or advanced automations.

## Communication cadence

- Critical: acknowledge same day and pause affected pilot scenario.
- Major: acknowledge within one working day and plan a fix or workaround.
- Minor/Improvement/Question: batch into weekly pilot update.
