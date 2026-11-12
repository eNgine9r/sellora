# Sellora Platform Admin Center — SA.1–SA.5

План спирається на [архітектуру SA.0](ARCHITECTURE.md). Порядок інтеграції — SA.1 → SA.2 → SA.3 → SA.4 → SA.5. SA.4 функціонально залежить від SA.1–SA.2, тому недоступність product events не повинна блокувати читання підписок. Злиття SA.0 відкриває можливість окремо розпочати SA.1. Стани та умови передачі наведено у [STATUS.md](STATUS.md).

## SA.1 — Platform access foundation

**Scope.** Окремі grants, policy та platform guard, source marker для сесії, `GET /api/v1/platform-admin/me`, журнал platform audit, bootstrap/revoke за межами HTTP і внутрішня гілка `/platform-admin` з порожнім shell. Позначити platform routes окремою категорією в [endpoint inventory](../../backend/tests/security/test_endpoint_inventory.py). Схема й прапорець впроваджуються з default-deny.

**Залежності.** Злитий SA.0, чинні [JWT і session dependencies](../../backend/app/dependencies/auth.py), additive міграція від актуального head, ізольована PostgreSQL. Для staging потрібні перевірені cookie-session config і операторський процес керування grants.

**Acceptance criteria**

- [ ] При вимкненому прапорці platform API повертає `404`. За ввімкненого прапорця guard перевіряє чинну сесію та grant. OWNER, MANAGER і ANALYST без grant отримують `403` з чинною прямою сесією, а anonymous, legacy, legacy-upgraded, revoked і expired sessions не проходять platform guard.
- [ ] Оператор без жодного workspace отримує тільки capabilities своєї platform-ролі. Та сама сесія без членства не дає доступу до tenant-даних. Додавання або зміна `X-Workspace-ID` не змінює platform-дозволів.
- [ ] Новий запит після revoke втрачає доступ. Grant/revoke і їх аудит атомарні. Паралельний bootstrap дає один початковий grant. Для звичайного CRM проходять чинні login, upgrade, refresh, logout та RBAC regression.
- [ ] `/platform-admin` має окремий layout, стани loading/denied/error, очищає кеш при зміні оператора. Перевірено прямий URL, повтор запиту після refresh і відсутність workspace header. Backend відповіді мають `private, no-store`.
- [ ] Усі нові routes мають явний platform guard в inventory. На ізольованій PostgreSQL підтверджено single head, upgrade з наявними сесіями, backend-only доступ і безпечне вимкнення функції.

**Ризики.** Підвищення tenant OWNER, прирівнювання legacy upgrade до прямого входу, застарілі capabilities, помилка RLS. Покрити матрицею негативних тестів, перевіркою grant на кожний запит і окремим tenant regression.

## SA.2 — Workspace directory і читання підписок

**Scope.** Пошук, фільтри та пагінація магазинів, read-only workspace detail і subscription projection. UI українською за замовчуванням, із чинною англомовною локалізацією та спільними UI primitives. Додати loading, empty, filtered empty і error, доступну клавіатурну навігацію та мобільну таблицю або картки.

**Залежності.** SA.1 access та audit. [Workspace model](../../backend/app/models/workspace.py), [demo provenance](../../backend/app/repositories/audit_log_repository.py), [subscription projection](../../backend/app/services/subscription_service.py) і підтверджена видимість записів під фактичною DB role.

**Acceptance criteria**

- [ ] Admin і support бачать лише дозволені поля метаданих. Auditor і tenant-only користувачі отримують відмову. Запити на workspace detail і subscription перевіряють дозвіл до lookup, а підміна header не змінює path target.
- [ ] Fixtures з однаковим timestamp проходять keyset pagination без повторів або пропусків для фіксованої вибірки. Невалідний cursor чи фільтр відхиляється. На репрезентативному наборі зафіксовано план запиту та відсутність N+1.
- [ ] Demo визначається за server-side provenance. Показ деактивованих магазинів керується фільтром. UI і API коректно розрізняють `UNMANAGED`, активний термін і derived expiry, з одним `as_of` на сторінку.
- [ ] DTO та UI не містять клієнтських або контактних даних, raw audit, provider payloads чи секретів. Читання записує audit. На desktop і mobile працюють пошук, пагінація, detail, localized states та keyboard navigation.

**Ризики.** Розкриття даних через надмірну DTO, повільний глобальний search і хибний статус через legacy `subscription_plan`. Вузька проєкція, bounded pagination і спільна термінова логіка.

## SA.3 — Product events і активність

**Scope.** Додати `product_events`, вузькі серверні producers, агрегати та scoped timeline. Узгодити покриття й retention до ввімкнення writer. Показати визначення активності, UTC-період, початок і стан покриття в UI.

**Залежності.** SA.1 authorization/audit, SA.2 workspace detail, підтверджені доменні call sites та ізольована PostgreSQL для concurrency/rollback. Потрібні інвентар producer coverage, узгоджений retention і перевірена метрика втрат.

**Acceptance criteria**

- [ ] Повторні й конкурентні записи тієї самої бізнес-події зводяться до одного event. Rollback доменної транзакції прибирає event, зокрема у вкладеному потоці з `commit=False`.
- [ ] Тести покривають звичайний workspace, manual lead, Direct lead і погоджені order flows, включно з вкладеним сценарієм. Демо та історичний імпорт виключені. Таблиця coverage перелічує непідключені потоки.
- [ ] Відновлюваний збій event insert зберігає чинний бізнес-результат і сигналізує про втрату. Тест з вимкненим writer підтверджує відсутність event-операцій.
- [ ] Два workspace з різними fixtures підтверджують ізоляцію timeline, формули summary, UTC-границі, фільтри та обмеження періоду. Роль без `activity.read` отримує `403`.
- [ ] UI відрізняє нуль за покритий період від неповних даних, а payload, logs і DTO не включають PII або tenant-об'єкти. На типовому та максимальному запиті записано план виконання, latency і обсяг даних для рішення про масштабування.

**Ризики.** Подвійний облік, event hook усередині чужої транзакції, навантаження на CRM і завищена повнота показників. Потрібні стабільний source key, перевірка savepoint і явні coverage markers.

## SA.4 — Subscription operations

**Scope.** Узгодити правила внутрішніх trial-команд. За наявності погодження додати вузький API й UI для старту, подовження або завершення trial з reason code, підтвердженням, аудитом, version check та replay. Платіжні операції, плановий автоперехід, PSP та entitlements поза цим етапом.

**Залежності.** SA.1–SA.2, [subscription foundation](../subscription-foundation.md), верифікований доступ app role і письмово погоджені pilot eligibility, plan code, межі терміну, reason codes та максимальний вік прямої сесії. `SELLORA_PLATFORM_TRIAL_COMMANDS_ENABLED` за замовчуванням вимкнений. Без погодження статус write-частини SA.4 — `BLOCKED`; subscription view залишається доступним.

**Acceptance criteria**

- [ ] Набір дозволених і заборонених переходів відповідає погодженій політиці. Для `ACTIVE`, історичного керованого стану, деактивованих та demo workspace trial create відхиляється. Support, auditor, tenant OWNER і застаріла privileged session не можуть виконати команду.
- [ ] Повтор того самого ключа й payload повертає той самий результат. Змінений payload або workspace з тим самим ключем і stale version дають `409`. Два конкурентні create для відсутнього рядка та конкурентні зміни терміну мають лише один дійсний перехід.
- [ ] Збій audit або команди відкочує term та idempotency record. Revoke і зміна терміну серіалізовані. У двох workspace доведено, що змінюється тільки дозволена path target.
- [ ] Чинний OWNER endpoint відображає зміну терміну з тими самими UTC-правилами, `enforcement_enabled=false`. Немає записів у payment receipts або змін у legacy `subscription_plan`.
- [ ] UI показує поточний і запропонований термін, пояснює stale/retry/denied, повтор зберігає той самий ключ. Перевірено focus, мобільне підтвердження й відсутність write controls за вимкненого прапорця.

**Ризики.** Ручне надання платного статусу, втрата терміну через гонку, неоднозначний retry. Обмежити дії trial, застосувати row lock, expected version і атомарний audit.

## SA.5 — Security review та staging-пілот

**Scope.** Read-only журнал для admin/auditor, огляд доступів і відхилень, затвердження retention, операційна інструкція grant/revoke, відновлення доступу, rollout/off switch, моніторинг і staging QA. Підготувати окреме рішення щодо production rollout.

**Залежності.** SA.1–SA.3 і погоджений стан SA.4. Якщо SA.4 заблокований, staging-пілот можливий лише з read-only підписками. Потрібні staging-акаунти для всіх platform/tenant ролей, два synthetic workspace, погоджена політика privileged authentication (зокрема MFA або approved equivalent перед production), retention й відповідальні за інциденти.

**Acceptance criteria**

- [ ] Audit endpoint класифікований як platform-only. Admin та auditor бачать redacted rows, support і tenant-only отримують `403`. Фільтри, стабільні cursors і доступ до самого журналу покриті тестами.
- [ ] На staging записано evidence для grant, revoke, відмови, привілейованого читання, fail-closed при помилці audit, subscription replay за ввімкненого write-path і незмінної tenant isolation. Якщо write-path вимкнений, зафіксовано причину й окремо перевірено read-only сценарій.
- [ ] Підтверджено RLS/grants під staging app role і відсутність клієнтського доступу до нових backend-only таблиць. Після off switch API та UI закриті, звичайні CRM-потоки проходять regression.
- [ ] Runbook визначає процедури grant/revoke і відновлення доступу, контроль доступу до журналу, retention, alert criteria для denied spikes, audit failures, dropped events, відкат застосунку й відновлення даних. Пілот має задокументованого відповідального і рішення `GO` або `NO_GO` з evidence.

**Ризики.** Витік через raw audit, відсутність оператора для відновлення, непомічені втрати activity, привілеї app role, неповні докази rollout. Пілот використовує synthetic fixtures і незалежні вимикачі. Production rollout потребує окремого рішення після staging.
