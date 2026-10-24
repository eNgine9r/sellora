# Sellora cinematic homepage — final design QA

Date: 2026-10-24. Scope: public `/`, UA/EN, selected first visual direction.

## Visual truth and browser evidence

- Selected image: [reference](docs/qa/homepage/reference.webp).
- Browser-rendered implementation: [desktop hero](docs/qa/homepage/desktop.webp), [workflow](docs/qa/homepage/workflow.webp), [mobile](docs/qa/homepage/mobile.webp).
- Desktop CSS viewport and screenshot: 1363 × 936, density 1.
- Source: 973 × 1616 pixels. For comparison it was scaled proportionally to 1363 px width and its first 936 px compared alongside the actual hero. The workflow source region was compared separately alongside the actual workflow capture. No browser chrome in either source or desktop capture.
- Actual responsive iframe viewports: 360/390/768 CSS px wide, 850 px high. With desktop scrollbars the measured content widths were 345/375/753 px. DOM scrollWidth equalled clientWidth at all three widths. This tests real CSS layout in Chromium, not a physical iPhone or Safari emulation.
- Full-view comparison: `/workspace/scratch/sellora-final-comparison.jpg`; focused workflow comparison: `/workspace/scratch/sellora-final-story-comparison.jpg`. Both were opened together with source and implementation in the same comparison input.
- Rejected evidence: a full-page capture omitted an offscreen composited hero. Accepted viewport captures above visibly contain the artwork.

## Comparison history and fixes

1. First pass was blocked: flat headline/CTA colors, underspecified story panel, no mobile runtime check and Ukrainian illustration in English mode.
2. Fixed: restored violet/coral palette, generated matching shipment art, added actual editable customer/product/payment/shipping context in the demo panel and localized illustration. Added scroll-linked perspective, pointer response, animation cleanup and an explicit motion toggle.
3. Contrast review found a 4.25:1 legacy hover color; corrected hover to retain the accessible base gradient without brightness filtering.
4. Visual comparison found the story heading wrapping to three lines instead of the intended two and a smaller hero display scale. Fixed display sizing, explicit localized two-line story heading and primary CTA dimensions. Recaptured the rebuilt page and compared again; the earlier wrapping issue is gone on desktop. Mobile uses its own readable wrapping.

## Required fidelity surfaces

- Typography: existing project sans-serif retained, strong display hierarchy and short headline; final story heading follows the reference's two-line desktop structure. No clipped text in inspected viewports.
- Spacing/layout: centered hero, asymmetric story, restrained sections and responsive stacking. Core shared header/footer are intentionally retained for existing navigation, menu, language and legal behavior.
- Colors/tokens: white CTA text measured at 6.60:1 / 6.00:1 / 5.50:1 against the three gradient stops, including the corrected hover gradient. The display violet measures 4.06:1 against the canvas (large-text threshold 3:1). Muted context text measures 7.82:1. Landing-only dark tokens; violet/coral display text and darker CTA gradient preserve white-label legibility. No global private-app theme changes.
- Images: generated assets match the selected ribbon/plinth art direction. Hero UA WebP 151206 B, EN 126032 B, supporting shipment image 56326 B. Full background not replaced with CSS drawings; real library icons used for UI controls. The hero is a raster composition with animated CSS perspective, not WebGL geometry.
- Copy/content: all editable text uses existing UA/EN dictionaries. Illustrative text switches to a dedicated English asset. Demo data is explicitly labeled, no real shop/customer information is used. Meta imports are described as manual and pilot-scoped; absent costs never produce fabricated profit.

## Interactions and accessibility checked

- Demo anchor reaches workflow; all four tabs and next-step buttons work.
- ArrowRight and End change the selected tab and its panel through keyboard navigation.
- Mobile menu opens; workflow link closes menu and navigates to the section.
- UA/EN selection changes headline and hero image source.
- Motion toggle sets `data-motion=off`, clears transform variables and removes animation. Scroll events change perspective when enabled. Narrow layouts suppress transforms.
- `prefers-reduced-motion` CSS and dynamic preference listener are implemented and reviewed; the OS preference itself was not forced in this browser. Explicit user-toggle fallback was exercised.
- FAQ opens with the profit explanation. Existing `/login` and three legal URLs remain correctly linked.
- Browser error logs inspected: only extension-origin metadata errors; no application-origin errors observed.

## Engineering validation

- Next.js production build passed after the final visual changes (34 generated routes).
- Full ESLint and TypeScript passed for the implementation; final build also linted/typechecked the subsequent typography-only update.
- Mobile static regression passed (31 routes).
- Vercel deployment-budget regression passed; main and dedicated QA remain the only auto-deploy branches.
- `git diff --check` passed.
- PR CI must pass on the exact published head before merging. Deployment verification is a separate post-merge step.

## Intentional adaptations / remaining P3

The source is a concept, not a literal product screenshot. Existing shared brand/navigation are retained. The workflow is an interactive, synthetic sale summary rather than a nonfunctional copy of the entire CRM screenshot. Additional capabilities, integration caveats and FAQ below the supplied frame are part of the requested content refresh. These are intentional functional adaptations.

Physical-device Safari QA and measured Core Web Vitals remain useful follow-up checks; neither is claimed here. No auth/provider backend behavior was tested or changed.

final result: passed
