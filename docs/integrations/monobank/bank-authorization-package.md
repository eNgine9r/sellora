# Sellora × monobank — пакет авторизації (11.11.2026)

**Статус:** підготовлено для звернення; **банк не погодив доступ**, токени та приватні ключі не встановлено. Перший merchant-пілот: Your Jewelry. No outbound Direct from Sellora.

## 1. Потрібні два офіційні канали

| Потреба | Рекомендований шлях для погодження | Що запитуємо |
|---|---|---|
| Доступ до надходжень на IBAN/бізнес-картку ФОП | Provider API або належно авторизований AISP через Open Banking (вибір підтверджує monobank) | Читання виписок за згодою власника, scope для обраного рахунку, ідентифікатори транзакції та правила rate-limit |
| Статуси оплати mono-посилань | Merchant Acquiring API | Лише `GET /api/merchant/invoice/status`, `GET /api/merchant/statement`, `GET /api/merchant/pubkey`, якщо банк дає обмежені права; webhook X-Sign |

**Не приймати припущення про ліцензію:** Open Banking AISP є регульованим процесом; банк має визначити, чи доступний він для заявника. Наявність API для провайдерів також не є автоматичною згодою використовувати його будь-якому SaaS. **Персональний API токен не використовувати як універсальне SaaS-рішення**.

**Merchant X-Token не гарантовано read-only:** той самий тип токена в офіційному API використовується для `POST /api/merchant/invoice/cancel` (скасування успішної оплати). До уточнення scope/ізоляції зберігати **нуль активних merchant банківських ключів** у production backend.

## 2. Реєстрація в corporate provider API

Офіційна документація: https://api.monobank.ua/docs/corporate.html

Публічний endpoint `POST https://api.monobank.ua/personal/auth/registration` описує:
- поля тіла: `pubkey` (base64 X.509/PEM public **secp256k1**), `name`, `description`, `contactPerson`, `phone`, `email`, `logo` (base64 файлу);
- заголовки `X-Time` (UTC timestamp), `X-Sign` для `X-Time | URL`;
- перевірку статусу `POST /personal/auth/registration/status`, а після approval банк повертає `keyId`.

**Не підписувати та не подавати автоматично до з'ясування канонічного payload алгоритму X-Sign і правового статусу заявника.** Генерація приватних ключів — окрема власницька безпечна процедура; тільки public key входить до заявки.

Для офлайн-перевірки даних:

```bash
python backend/scripts/monobank_registration_preflight.py \
  --profile /secure/non-git/company-profile.json \
  --public-key /secure/non-git/secp256k1-public.pem \
  --logo /secure/non-git/sellora-approved-logo.jpg

# Після успішної перевірки і погодження банком:
python backend/scripts/monobank_registration_preflight.py \
  --profile /secure/non-git/company-profile.json \
  --public-key /secure/non-git/secp256k1-public.pem \
  --logo /secure/non-git/sellora-approved-logo.jpg \
  --output /secure/non-git/monobank-registration-body.json
```

Скрипт **не має мережевих функцій**, не торкається приватного ключа, не створює підпис і не звертається до monobank. Результат з контактною інформацією створює лише з mode `0600` і ніколи не додає в GitHub.

## 3. Офіційний лист (шаблон)

**Тема:** Sellora — погодження інтеграції з monobank (виписки ФОП та статуси еквайрингу)

> Добрий день! Розробляємо Sellora — SaaS CRM/ERP для онлайн-магазинів. Перший пілотний магазин Your Jewelry отримує оплати переказом на IBAN ФОП, на бізнес-картку ФОП і через платіжні посилання monobank.
>
> Просимо надати порядок авторизації Sellora як сервісу, який за підтвердженою згодою власника рахунку **лише читає дані про зарахування** та звіряє їх з існуючими замовленнями, без ініціювання переказів або повернень коштів.
>
> Просимо уточнити: (1) юридичні та технічні умови provider API / Open Banking AISP; (2) необхідні документи для реєстрації компанії/ФОП; (3) sandbox і процес погодження; (4) доступні read-only scopes та обмеження для рахунків ФОП; (5) чи можливий status-only merchant токен або альтернативний погоджений механізм без права refund; (6) webhook/public key, відновлення пропущених подій, частоту виписок.
>
> Додаємо технічний паспорт. Контакт: [ПІБ], [юридичний заявник], [email], [телефон].
>
> Дякуємо! Команда Sellora.

Надсилати через підтверджену офіційну підтримку https://monobank.ua/openbanking або інший канал, який надасть банк. Не припускати існування окремого «публічного email для API», поки він не підтверджений банком.

## 4. Вимоги безпеки перед активацією

- Owner-initiated explicit consent для конкретного workspace і рахунку. RBAC та audit trail.
- Не зберігати bank personal API tokens в SaaS; не просити їх у чаті чи GitHub.
- Ключі лише в ізольованому secrets runtime з ротацією, аудитом і планом термінового відкликання.
- Merchant: банк має підтвердити обмеження прав або погодити ізольований proxy; **GET-only код не робить X-Token обмеженим на стороні банку**.
- Webhook: перевірка підпису ECDSA raw body з bank pubkey; події лише тригер рефетчу, не причина автоматичного `PAID`.
- DB: dedup workspace/provider/account/transaction; payout еквайрингу не є другим замовленням; missing/hold/refund/partial/ambiguous → manual REVIEW.
- Run through sandbox + bank E2E, відповідні privacy/consent/legal перевірки, security audit, staging, owner approval, canary.

## 5. Що ще має повідомити власник

1. Юридичний заявник (назва ФОП чи компанії, ідентифікація — лише через захищений канал).
2. Контактна особа, корпоративний email і телефон.
3. Офіційний домен Sellora та документи privacy/terms, якщо банк вимагає.
4. Чи є активний merchant еквайринг mono і чи власник може підтвердити згоду на обрані ФОП рахунки.

**Не надсилати секрети** (merchant X-Token, персональний токен, приватний ключ), PAN картки чи виписки покупців.

## 6. Готовність

- [x] Базовий payment evidence ledger / RBAC / RLS / review-only CSV на staging.
- [x] Обмежені внутрішні GET-client primitives і ECDSA verifier (але не live connector).
- [x] Підготовлена структура заявки, локальний preflight і документація.
- [ ] Погоджений банком правовий механізм, назва заявника, owner consent.
- [ ] Схвалені scopes/креденшали з безпечним зберіганням; sandbox/E2E.
- [ ] Підтверджена реальна звірка Direct receipt → existing itemized Order → bank payment allocation і тести на returns.
- [ ] Bank integration GO LIVE після security і owner approval.

Довідково:
- https://api.monobank.ua/docs/corporate.html
- https://monobank.ua/openbanking
- https://api.monobank.ua/docs/index.html
- https://monobank.ua/api-docs/acquiring/methods
- https://monobank.ua/api-docs/acquiring/dev/webhooks/get--api--merchant--pubkey
