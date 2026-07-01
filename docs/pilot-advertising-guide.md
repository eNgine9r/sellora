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
