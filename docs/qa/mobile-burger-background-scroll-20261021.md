# Mobile hamburger navigation — background scroll leak

**Severity:** P1
**Affected screen:** Authenticated Sellora mobile AppShell; same lock pattern on public mobile header.
**Issue:** The hamburger menu used a body-only overflow class. The AppShell container has overflow-x-hidden, which can create an independently scrolling vertical surface on mobile. The user could scroll content behind the open navigation overlay.

## Expected
- Opening hamburger fixes the underlying page at the current position.
- The menu's own long navigation list is scrollable without moving background content.
- Dismissing via overlay, choosing a route or pressing Escape restores original scroll position and styles.
- The menu lock cooperates with any nested modal/sheet, including on mobile Safari; no double-release.
- No data changes, API writes, Meta sends, Nova Poshta, accounts or orders during QA.

## Fix
- Use existing shared reference-counted acquireOverlayScrollLock() utility instead of body overflow class; release on close/unmount.
- While mobile menu is open, set AppShell container overflow to clip so its overflow-x-hidden cannot create an independent y scroll container.
- Keep the sidebar nav as an independently scrollable overscroll-contained region and clip the outer panel instead of creating a scrollable parent.
- Escape closes the menu; public mobile header uses the same centralized lock.
- Frontend only; no Raspberry backend changes.

## QA
- TypeScript, ESLint, Next.js Vercel production build.
- Google Chrome synthetic-auth tests at 390px and 320px; test background wheel/touch attempts while menu open, menu internal wheel scroll, Escape/backdrop close and restoration. Network writes blocked.
- Public mobile header with real unauthed landing page: backdrop close, viewport restored.
- Real iOS Safari device QA remains separate from Chromium emulation.
