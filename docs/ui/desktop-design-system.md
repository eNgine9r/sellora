# Sellora Desktop Design System — Sprint Dd.1

## Tokens

The dark SaaS foundation is defined as semantic CSS variables in `frontend/src/app/globals.css`.

- Canvas: `--canvas` `#070A14`
- Sidebar: `--sidebar` `#090C18`
- Surfaces: `--surface-1`, `--surface-2`, `--surface-3`, `--surface-hover`
- Borders: `--border-subtle`, `--border-strong`
- Text: `--text-primary`, `--text-secondary`, `--text-muted`
- Actions: `--primary-solid`, `--primary-hover`, `--primary-active`, `--focus-ring`
- Feedback: `--success`, `--warning`, `--danger`, `--info`
- Brand gradient: `--brand-gradient` from purple to magenta to orange

Use semantic utilities such as `bg-surface-1`, `text-text-primary`, `border-border-subtle`, and `bg-primary`. Do not put raw hex colors in page components.

## Typography

- Page titles use bold, tight tracking, and `text-text-primary`.
- Secondary explanatory copy uses `text-text-secondary` and clear Ukrainian product language.
- Muted metadata uses `text-text-muted`.

## Spacing and radius

- Default page gap: `--space-page` = `24px`.
- Controls: 32px small, 40px default, 44px large.
- Cards: `--radius-card` = `16px`.
- Shell/dialog panels: `--radius-shell` = `24px`.

## Buttons

Use `Button` from `src/components/ui/primitives.tsx`.

- `primary`: solid purple for normal primary actions.
- `brand`: gradient only for global Create CTA or rare brand accents.
- `secondary`: bordered dark surface for neutral actions.
- `ghost`: low-emphasis icon/text actions.
- `danger`: destructive confirmation actions.

All buttons include hover, active, focus-visible, disabled, and loading states.

## Fields

Use `FormField`, `Input`, `Select`, `Textarea`, and `Checkbox` for future form work. Labels, hints, validation, disabled/read-only behavior, and autocomplete should be explicit at the call site.

## Cards and page headers

Use `Card` for dark surfaces with subtle border and standard shadow. Use `PageHeader` for consistent title, description, and action layout.

## Badges

Use `StatusBadge` for visual tone. Backend enum values must remain English; labels are translated at UI level.

## Tables

Use `DataTable` as the desktop table foundation:

- table scroll is inside the table container;
- body should not horizontally scroll;
- loading, empty, filtered-empty, and error states are supported;
- pagination belongs in a slot below or beside the table depending on page layout.

Mobile cards from Sprint Dm.1 must remain in place; desktop tables do not replace mobile cards.

## Drawers and modals

`Drawer`, `Modal`, and `ConfirmationDialog` in `src/components/ui/overlay.tsx` share overlay behavior:

- ESC closes;
- focus is trapped inside the overlay;
- focus returns to the trigger after close;
- body scroll is locked;
- drawer is 460–520px on desktop and full-screen below tablet widths;
- drawer has sticky header and optional sticky footer.

## States

`LoadingSkeleton`, `EmptyState`, and `ErrorState` use semantic dark surfaces. Empty states should tell users what to do next, for example creating an order or importing products.

## Responsive rules

- App shell uses a 240px desktop sidebar.
- Main content has `min-width: 0`, stable padding, and no body-level horizontal scroll.
- Mobile bottom navigation, mobile drawer navigation, and profile/workspace sheets are preserved.
- Forms collapse to one column on mobile.

## Accessibility rules

- Every interactive control must have visible focus states.
- Icon-only controls require `aria-label`.
- Dialogs and drawers require semantic `role="dialog"`, `aria-modal`, labelled headers, and keyboard escape handling.
- Do not rely on color alone for statuses; include text labels.

## Correct usage examples

```tsx
<PageHeader title="Замовлення" description="Керуйте оплатами, статусами й відправленнями." actions={<Button>Створити замовлення</Button>} />
<Card>...</Card>
<FormField label="Телефон" error={phoneError}><Input autoComplete="tel" /></FormField>
<StatusBadge tone="success">Оплачено</StatusBadge>
```

## Public page additions — Sprint Dd.2

Public landing and auth pages use the same dark tokens as the protected App Shell, but may be more expressive through larger typography, restrained glow, and brand-gradient CTAs.

Rules:

- Use `PublicHeader`, `PublicFooter`, `PublicSection`, and `MarketingCTA` for public pages.
- Keep brand gradients limited to primary marketing CTAs and decorative background glow.
- Use `/login` as public primary CTA unless a real registration or beta request flow exists.
- Product previews with illustrative numbers must be marked as demo.
- Integration cards must use truthful statuses and must not expose mock, staging, dry-run, or internal readiness wording.
- Login pages must avoid technical auth vocabulary and preserve the existing auth/session implementation.

## Dual-theme hardening — Sprint Dd.2.1

Semantic tokens must define light values in `:root` and dark values in `.dark`. New UI must avoid assuming a dark canvas.

Required token families include canvas, sidebar, surfaces, selected/hover/elevated surfaces, borders, primary foreground, input background/border, overlay background, feedback surfaces/foregrounds, text disabled, focus ring, and shadow color.

Primary buttons must use `primary-foreground` rather than hardcoded white text. Feedback states should use semantic feedback surface and foreground tokens.

## CRM workspace additions — Sprint Dd.3

Protected CRM pages use a compact application pattern rather than public marketing sections:

- Page headers are compact, tokenized, and action-oriented.
- KPI cards use semantic surfaces, text, borders, and status tones in both themes.
- Summary rows are compact and may be clickable only when they apply real existing filters.
- Entity drawers use the shared overlay foundation and must stay keyboard accessible.
- Unsupported metrics or backend-derived states should be shown as unavailable rather than estimated or fabricated.

Dd.3–Dd.7 rule: every new or modified page/component must support and be validated in both light and dark themes on desktop and mobile.
