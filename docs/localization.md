# Sellora Localization

## Supported locales

Sellora currently supports:

- `uk` — Ukrainian
- `en` — English

The default locale is `uk`.

## Translation file structure

Frontend dictionaries live in:

- `frontend/src/i18n/messages/uk.json`
- `frontend/src/i18n/messages/en.json`

The dictionaries are grouped by product area: `common`, `navigation`, `auth`, `landing`, `dashboard`, `leads`, `customers`, `orders`, `products`, `inventory`, `shipments`, `advertising`, `analytics`, `settings`, `importCenter`, `novaPoshta`, `statuses`, `errors`, `emptyStates`, `actions`, and `tables`.

## Adding new keys

1. Add the same key to both locale files.
2. Use `useI18n()` in client UI components.
3. Read strings with `t("section.key")`.
4. For structured arrays, use `tr<T>("section.key")`.
5. Avoid hardcoded user-facing Ukrainian or English in components.

## Enum translations

Backend/API/database enum values must stay unchanged. For example, the API value `DELIVERED` is displayed as `Доставлено` in Ukrainian and `Delivered` in English.

Use frontend-only helpers:

- `formatStatus(group, value)` from `useI18n()` for runtime UI labels.
- `formatEnumStatus(group, value, locale)` for non-hook contexts.

Do not send translated statuses back to the backend. Forms may display localized labels, but submitted values must remain backend enum values such as `NEW`, `DELIVERED`, `PAID`, `ACTIVE`, or `DRAFT`.

## Persistence

The selected locale is persisted in `localStorage` with key `sellora_locale`.

Rules:

- Missing locale falls back to `uk`.
- Invalid locale falls back to `uk`.
- Changing language updates the UI immediately.
- Reloading keeps the selected language.

## QA checklist

- First visit defaults to Ukrainian.
- Switch to English from the topbar language switcher.
- Switch language from Settings.
- Reload and confirm the selected language persists.
- Confirm status badges are localized but API enum payload values are unchanged.
- Confirm mobile topbar and drawer do not overflow with the language switcher.
