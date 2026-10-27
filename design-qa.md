# Sellora scroll journey and login — design QA

Date: 2026-10-24. Scope: public homepage and login, Ukrainian and English.

## Accepted direction and evidence

The selected dark cinematic direction is retained in typography, violet/coral accents and depth. The user's subsequent correction explicitly replaces the Instagram-centered raster hero and manual demo with scroll-driven CRM storytelling, and extends the same visual language to login. This revision is checked against that revised scope rather than claiming pixel fidelity to the earlier static concept.

Browser viewport: Chromium, 1363 × 936 CSS px. Accepted viewport evidence:

- [CRM overview](docs/qa/homepage/desktop.webp)
- [Order foreground](docs/qa/homepage/workflow.webp)
- [Financial foreground](docs/qa/homepage/finance.webp)
- [Login](docs/qa/homepage/login.webp)
- [Mobile homepage](docs/qa/homepage/mobile.webp)
- [Mobile login](docs/qa/homepage/login-mobile.webp)

All captures were opened and inspected. Mobile evidence uses real CSS iframe viewports in Chromium; it is not physical-device or Safari testing.

## Motion verification

The animation uses independent DOM UI layers, native sticky positioning, perspective and interpolated camera poses. Native scroll controls timeline progress; it is not a tilt applied to a flattened image. No additional animation dependency or scroll interception was introduced.

Observed desktop progression using PageDown: overview → enquiry at scrollY 1402 → order at 2221 → shipping at 3040 → finances at 3859. PageUp returns from finances to shipping. The sticky scene top stays at 76 px until its natural release at the end. The order transform near its chapter was translate3d(0.094px, 9.941px, 149.882px), scale 1.1198; the finance transform reaches translate3d(0px, 10px, 150px), scale 1.12. Background layers move independently and recede.

The initial runtime check exposed an existing body overflow rule that made sticky descendants follow a non-scrolling ancestor. Fixed with an html/body overflow correction scoped through the landing component; private application layout is unaffected. Reproduced before and after: sticky top changed from −742.9 px to 76 px at scrollY 1402.

An overview finance card initially overlapped the scene caption. Its overview pose was corrected. Final observed bottom is 735.8 px, above the caption at 759.3 px. The focused finance chapter remains large and readable.

- Chapter buttons navigate the native scroll timeline; navigation to capabilities leaves the scene normally.
- Capability sections reveal on entering the viewport; content remains visible without enhancement.
- Mobile and short viewports use normal document flow and entering cards rather than a long pinned sequence.
- Explicit Reduce motion / Enable animation toggle tested: aria-pressed and data-animated change, transforms clear, the static grid remains readable.
- OS prefers-reduced-motion listener and CSS reviewed. The OS setting was not forced through this browser.
- Animation work is scheduled once per scroll frame, suspended outside the section and when the document is hidden; listeners and observers are cleaned up.

## Responsive and login checks

Actual iframe viewports: 360, 390, 768 and 1024 px wide × 850 px high. Measured document widths / scroll widths: 345/345, 375/375, 753/753, 1009/1009 (desktop scrollbars account for the difference). No horizontal overflow. The 1024 px view enables the full scene; 768 px and narrower use the compact sequence.

- Login: desktop split composition, readable card, mobile form, correct email/password autocomplete and input types.
- Empty submission shows a localized inline error and focuses the invalid field without an authentication request.
- Password visibility toggle changes type and aria-pressed.
- Switching UA/EN translates headings, preview content and an already-visible validation error.
- Mobile menu opens with aria-modal=true and closes with Escape.
- Legal links and existing login/dashboard route behavior retained.
- Browser error logs: extension-origin metadata errors only in inspected entries, no observed application-origin runtime errors.

Successful authenticated login, invalid account/network API responses, physical iPhone/Safari and measured Core Web Vitals were not exercised. Existing auth service, session storage, API contracts and backend are unchanged; the auth boundary regression passes.

## Content and accessibility

Sellora is presented as a CRM for customers, orders, inventory, delivery and finances. Instagram appears only in the integration listing, with a pilot label. Future platforms are explicitly planned, not claimed as available. Footer, metadata and manifest use the broader CRM positioning.

All preview data is synthetic and labeled as a demonstration. The example profit is 679 − 300 − 80 − 20 = 279 UAH, with all sample costs known. Product copy explains that unknown cost is not zero. No uploaded shop/customer data is used.

UA/EN strings use the existing dictionaries. Existing shared branding and public navigation are retained. Controls have names, focus outlines, selected/current states and text status labels. Motion control and OS preference have a readable fallback.

## Engineering checks

- Full ESLint: passed.
- TypeScript: passed.
- Production build: passed, all 34 routes generated.
- All 14 frontend static scripts called by frontend-production CI: passed locally.
- Mobile static audit: passed, 31 routes.
- Auth/API boundary: passed, 11 checks.
- Deployment budget gate: passed; auto-deployment remains limited to main and the dedicated QA branch.
- git diff --check: passed.

Exact published-head CI and post-deployment browser smoke are release gates, recorded in the PR/deployment rather than preclaimed here.

## Remaining P3 follow-up

Physical Safari testing and measured performance profiling on a low-end phone are useful follow-up checks. No outstanding P0/P1/P2 issues in the exercised public flows.

final result: passed
