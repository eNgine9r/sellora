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
- Manual campaign attribution для лідів і замовлень є optional і вибирається за назвою кампанії.
- Lead/order forms do not require campaign_id; empty campaign values remain valid and appear as unattributed.
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

## Manual attribution MVP — Sprint 4.4

For pilot usage, campaign attribution is manual. When creating or editing a lead or order, the user may optionally choose a campaign by name. If no campaign is known, leave the field empty; this is expected and should not block lead or order workflows.

The `/advertising` attribution section shows campaign-linked orders, attributed revenue, attributed net profit, and unattributed orders based only on manual campaign links. It does not use Meta Ads OAuth, automatic sync, or automatic Instagram Direct matching. Secure staging credentials must be provided outside this report, and synthetic data should be used for QA.

Advertising CSV import is still not pilot-ready until manual staging QA for import passes. Sprint 4.3 full build/browser approval also remains blocked where frontend lockfile and dependency installation are unavailable.
