# Pilot Advertising Guide / Реклама для пілотного магазину

Sellora зараз працює з ручним імпортом рекламних метрик. Автоматична інтеграція Meta Ads буде додана пізніше; зараз вона не активна.

## Навіщо імпортувати рекламу

Імпорт реклами показує, чи окупаються кампанії Instagram/Meta: скільки коштують повідомлення, ліди й замовлення, і скільки доходу приносить реклама.

## Як часто імпортувати

Для пілоту достатньо імпортувати дані щодня або кілька разів на тиждень. Головне — обирати той самий період у `/advertising`, Dashboard і Analytics.

## Як заповнити шаблон

1. Завантажте шаблон `/templates/advertising-import-template.csv`.
2. Залиште колонки `Дата`, `Кампанія`, `Платформа`, `Витрати`, `Повідомлення`, `Ліди`, `Замовлення`, `Дохід`, `Чистий прибуток`, `Покази`, `Кліки`.
3. Для першої перевірки використовуйте тільки synthetic DEMO рядки.
4. Не додавайте токени, ID рекламного кабінету, персональні дані клієнтів або приватні нотатки.

## Що означають метрики

- ROAS 5 означає, що кожна 1 грн реклами принесла 5 грн доходу.
- CPA 200 грн означає, що одне замовлення з реклами коштувало 200 грн.
- CPL 50 грн означає, що один лід коштував 50 грн.
- ROI показує співвідношення чистого прибутку до рекламних витрат.

## Як порівнювати кампанії

Порівнюйте кампанії за однаковий період. Кампанія з більшим ROAS і нижчим CPA/CPL зазвичай ефективніша, але також дивіться на кількість замовлень і чистий прибуток.

## Поточні обмеження

- Дані реклами вводяться вручну або через імпорт.
- Campaign attribution для лідів і замовлень залишається optional.
- Lead/order forms do not require campaign_id.
- Future Meta Ads attribution remains future work and will use official APIs only.
- Якщо у рядку немає лідів або замовлень, Sellora показує `—`, а не `NaN` чи `Infinity`.

## Sprint 4.3 — Як читати рекламні інсайти

На сторінці `/advertising` Sellora тепер показує порівняння кампаній, найкращі кампанії та кампанії, які потребують уваги. Це не AI-рекомендації й не Meta Ads sync: висновки рахуються тільки з ручних або CSV-імпортованих метрик за вибраний період.

Статуси рішень:

- **Добре працює** — ROAS достатньо високий, кампанія може бути кандидатом на масштабування.
- **Потрібно спостерігати** — є сигнали, але перед масштабуванням треба перевірити CPA/CPL, ліди та замовлення.
- **Потребує уваги** — є витрати без замовлень; кампанію варто зупинити або переглянути.
- **Недостатньо даних** — Sellora не робить висновок, якщо витрат або подій недостатньо.

Advertising import все ще не позначено pilot-ready, доки ручна staging QA з synthetic CSV шаблоном залишається заблокованою.

## Sprint 4.3.1 — NO_DATA та пріоритет правил

Кампанія без рекламних метрик тепер має бути видимою у порівнянні зі статусом **Недостатньо даних** і повідомленням **Недостатньо рекламних даних для висновку.** Така кампанія не потрапляє у найкращі кампанії й не отримує рекомендацію масштабування.

Пріоритет правил: **NO_DATA → PROBLEM → GOOD → WATCH**. Якщо є витрати й ліди, але немає замовлень, Sellora показує **Потребує уваги** з повідомленням: **Ліди є, але замовлень немає — перевірте обробку Direct або пропозицію.**

Advertising import все ще не позначено pilot-ready, доки ручна staging QA імпорту не пройде з synthetic CSV даними.

## Sprint 4.5 — Як читати рекламний звіт

Сторінка `/advertising` тепер подана як бізнес-звіт для власника магазину: спочатку видно джерело даних, далі KPI, підказки по кампаніях, пояснення ручної атрибуції, порівняння кампаній, денні метрики, тренд і блок готовності до pilot review.

Важливо:

- рекламні метрики беруться тільки з ручного внесення або CSV-імпорту;
- атрибуція лідів і замовлень є ручною через вибір кампанії у формі;
- замовлення без кампанії залишаються валідними;
- Meta Ads API та автоматична атрибуція залишаються майбутньою роботою;
- advertising import не є pilot-ready, доки staging QA імпорту не пройде з synthetic CSV даними.

## Sprint 4.6 — Meta Ads API readiness, без live інтеграції

Meta Ads API ще не активний. Sprint 4.6 тільки документує майбутню архітектуру OAuth, workspace isolation, encrypted token storage, read-only sync і безпечний контракт мапінгу даних.

Для pilot-користувачів зараз залишається актуальним:

- ручне внесення рекламних метрик;
- CSV-імпорт шаблону;
- ручна атрибуція лідів/замовлень до кампаній;
- жодних live Meta токенів, ad account IDs або реальних експортів у QA артефактах.

Майбутня read-only Meta sync має імпортувати delivery metrics кампаній. Замовлення, дохід і прибуток залишаються даними Sellora. Conversions API потребує окремого sprint, legal/privacy review і явного рішення продукту.

## Sprint 4.7 — Fake Meta sync для майбутньої інтеграції

Sellora має backend-only fake client для безпечної симуляції майбутньої Meta sync. Це не live інтеграція: Meta Ads API ще не активний, токени не зберігаються, запити до Meta не виконуються, а production sync jobs не запускаються.

Для pilot-користувачів активними залишаються ручне внесення рекламних метрик і CSV-імпорт. Майбутня Meta sync має імпортувати лише delivery metrics кампаній; замовлення, дохід і прибуток залишаються даними Sellora.

## Sprint 4.8 — Sync preview без змін у базі

Sellora має read-only preview для майбутньої Meta sync. Він показує, що потенційно було б створено, пропущено або позначено як конфлікт, але не записує дані в базу.

Ручні та CSV-метрики захищені: якщо fake Meta row перетинається з існуючим рядком, Sellora показує `POTENTIAL_CONFLICT`, а не оновлює дані автоматично. Live Meta Ads API, токени, production sync jobs і Conversions API все ще не активні.

## Sprint 4.9 — Future Meta identity contract for pilot reviewers

Meta Ads API remains not active. Sprint 4.9 only documents how future Meta-synced campaigns and metrics will be identified separately from manual and CSV rows.

Future Meta sync should use workspace-scoped external identity (`external_source`, `external_account_id`, `external_campaign_id`) and source markers (`manual`, `csv_import`, `meta_sync`). Manual/CSV data is protected by default, and Meta rows must not overwrite owner-entered or imported rows unless they are already Meta-owned rows with the same external identity.

Orders, revenue, and profit remain Sellora-side. Advertising import remains not pilot-ready until staging QA passes, and Sprint 4.4 remains conditional until PostgreSQL runtime and browser/mobile QA pass.

## Sprint 4.10 — Runtime-gated schema draft note

Sellora has a draft schema step for future Meta identity/source separation, but Meta Ads API remains not active. The new fields are nullable and runtime-gated; they do not connect to Meta, do not store tokens, do not run sync jobs, and do not change manual/CSV advertising workflows.

Pilot reviewers should continue to treat manual entry and CSV import as the active source. Advertising import remains not pilot-ready until staging QA passes, and Sprint 4.4 PostgreSQL/runtime/browser blockers remain open.

## Sprint 4.11 — Meta Ads sync preview UX, feature gate, and admin review flow

Sprint 4.11 keeps Meta Ads API inactive and adds only UX, documentation, and regression coverage for a future review flow. The current active advertising source remains manual entry / CSV import, and advertising import is not pilot-ready until staging/runtime QA is completed.

### User-facing status and feature gate

- Frontend feature gate: `metaAdsSyncPreviewEnabled = false` by default.
- Current visible state: `NOT_ACTIVE` / `COMING_SOON` only.
- Meta Ads API is not active yet; there is no live OAuth route, no token input, no live Meta API call, no apply-sync button, and no production sync trigger.
- The disabled CTA says Meta Ads connection will be available in a future stage and cannot start OAuth or sync.

### Future sync preview UX labels

Display labels are frontend-only and must not become persisted backend/API enum values:

| Backend preview value | Ukrainian label | English label |
| --- | --- | --- |
| `WOULD_CREATE` | Буде створено | Will be created |
| `WOULD_UPDATE` | Буде оновлено | Will be updated |
| `WOULD_SKIP` | Без змін | No changes |
| `POTENTIAL_CONFLICT` | Потребує перевірки | Needs review |
| `NEEDS_EXTERNAL_ID_SUPPORT` | Потрібна підтримка Meta ID | Meta ID support needed |
| `INVALID` | Помилка в даних | Data issue |

### Future admin review flow contract

1. OWNER підключає Meta Ads у майбутньому етапі.
2. Sellora завантажує рекламні метрики у preview mode.
3. OWNER бачить, що буде створено, оновлено, пропущено або потребує перевірки.
4. Sellora не перезаписує ручні/CSV дані автоматично.
5. OWNER підтверджує тільки безпечні зміни у майбутньому apply-flow.
6. Sellora записує sync run після майбутнього підтвердженого запуску.

Sprint 4.11 does not implement steps 1, 5, or 6. Apply-sync, sync-run persistence execution, production sync jobs, token storage, and live OAuth remain future work.

### Manual/CSV protection

Sellora не перезаписує ручні або CSV-рекламні дані автоматично. Sellora does not automatically overwrite manual or CSV advertising data. Meta Ads provides spend, impressions, clicks, and messages where available; orders, revenue, and profit remain Sellora-side business data.

### Future UX states

Documented future states are `NOT_ACTIVE`, `COMING_SOON`, `PREVIEW_AVAILABLE`, `NEEDS_REVIEW`, `CONFLICTS_FOUND`, `READY_TO_APPLY`, `CONNECTED`, `SYNCING`, `SYNC_SUCCESS`, `SYNC_FAILED`, `TOKEN_EXPIRED`, `PERMISSION_MISSING`, and `DISCONNECTED`. Sprint 4.11 may only show `NOT_ACTIVE`, `COMING_SOON`, and feature-gated demo preview states; `CONNECTED`, `SYNCING`, and `SYNC_SUCCESS` remain future states and must not imply a live connection.

### Runtime-gated blockers remain

Sprint 4.10 runtime PostgreSQL migration QA remains skipped/pending, so Sprint 4.10 is not fully approved. Sprint 4.4 PostgreSQL runtime migration QA, advertising CSV import staging QA, browser/mobile/theme QA, and workspace/cross-workspace runtime QA remain open blockers.
