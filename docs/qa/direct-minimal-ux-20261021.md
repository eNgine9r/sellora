# Sellora Direct — Simplification Sprint (2026-10-21)

## Product decision

The primary user journey is **read customer message → assess intent → select product → confirm customer → manually create order**. On every viewport, keep the message timeline the most important surface.

**Desktop**: 290px conversation list + fluid message pane; do not reserve a permanent third-column AI panel.
**Mobile**: conversation list or single selected thread; visible Back action; use the shared details drawer for Profile / CRM / AI.
**Support**: hide bulk history imports behind explicit advanced menu, retain existing confirmation modal.

## QA issue log

| Severity | Location | Before | Required / implemented |
|---|---|---|---|
| P1 | Desktop Direct | Fixed 300px AI side panel competed with the chat even when empty | Remove persistent AI panel; on-demand 3-tab inspector |
| P1 | Direct | Tall card, customer/prospect details and extra service status stole space | Single short sales-context row; CRM details in inspector |
| P1 | Conversation list | Many equal-strength badges, borders, filters | Quieter cards, focus on name/unread/order status, 3 meaningful filters |
| P1 | Message bubbles | Every message repeated sender and provider state | Normal bubbles show only text; show delivery state when failed |
| P0 | Mobile 320–390px | Prior sprint allowed zero-height message pane | Test actual viewport height >=100px on 320/390, text visible |
| P1 | Mobile | Long send-disabled policy note collided visually with bottom navigation | Short mobile policy note; full warning preserved on desktop |
| P1 | History | Import UI prominent to everyday sellers | Move to Advanced drawer with existing confirmation modal |
| P1 | Privacy/reliability | Account and order side effects possible through browsing or fake CTA | Retain explicit customer/order actions, preserve backend workspace linkage guard and Meta send disabled |

## Automated browser check

Chrome QA uses a fully intercepted **synthetic user and synthetic conversations**; no real customer message bodies, token, order, lead or Meta send APIs are used.

- Viewports: 1440x900, 1024x768, 768x850, 390x844, 320x700.
- Must pass: no horizontal overflow; timeline >=100 px and synthetic message visible; stage classification visible; no permanent AI column; side drawer tabs Profile/CRM/AI interactive; no React runtime errors.
- Must pass: no real provider or CRM writes, and no automatic customer creation on just opening a conversation.
- The authorized Your Jewelry session was **not** accessed by these tests; real-data visual QA is separately pending.

## Release constraints

- Frontend-only: backend image, Meta flags, NP tracking and actual workspace records unchanged.
- Draft PR stacked on Direct Sales #277; **do not merge into main** until legacy Render deploy automation is safely retired.
- Vercel explicit staging alias from exact SHA after Chrome QA.
