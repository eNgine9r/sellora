# Sellora Pilot Release Notes — Pre-MVP

These notes are Ukrainian-first for guided pilot stores. Use synthetic or safe copied data only; do not paste private customer lists, full phone lists, API keys, tokens, private spreadsheets, or workspace IDs into feedback.

## Що готово для пілоту

- Dashboard з доходом, замовленнями, ROAS, топ товарами та залишками.
- Analytics reports для продажів, товарів, реклами, клієнтів, складу та business insights.
- Products, variants, inventory, orders, customers, leads, shipments.
- Manual/imported advertising metrics.
- Import Center з preview, mapping, validation, dry-run, warnings/errors і duplicate handling.
- Demo workspace із синтетичними DEMO даними.
- In-app feedback form для проблем, ідей, незрозумілих місць і оцінки.

## Що тестувати

1. Login і workspace selection.
2. Dashboard за різні періоди.
3. Створення товару, варіанта, замовлення і shipment.
4. Імпорт каталогу або історії замовлень через dry-run.
5. Рекламні метрики і ROAS.
6. Mobile view на телефоні.
7. Feedback flow із privacy hint.

## Що поки ручне

- Advertising metrics вводяться вручну або імпортуються з файлу.
- Instagram leads створюються вручну; Instagram Direct API ще не підключено.
- Meta Ads API ще не підключено.
- Nova Poshta потребує реальних settings/API validation для production сценаріїв.

## Як повідомляти фідбек

Натисніть **Фідбек** у topbar, оберіть категорію, за бажанням оцінку 1–5, опишіть проблему або ідею. Не додавайте паролі, API-ключі, токени або приватні дані клієнтів у повідомлення.

## Recommended test scenarios

- Empty workspace onboarding: чи зрозуміло, що робити першим?
- Demo workspace: чи зрозуміло, що дані синтетичні?
- Import dry-run: чи зрозумілі warnings/errors/duplicates?
- Analytics: чи збігаються цифри з очікуванням після імпорту?
- Mobile: чи можна виконати ключові дії з телефона?
