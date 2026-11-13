# SA.5 — QA Fixes & Staging Preparation

**Ізольований QA і захищений Platform Admin staging — PASS.** Виправлення та їхні regression tests злиті у [PR #417](https://github.com/eNgine9r/sellora/pull/417). База аудиту й підтверджені дефекти описані у [PR #416](https://github.com/eNgine9r/sellora/pull/416). Рішення щодо бойового середовища ведеться у [production preflight](../PRODUCTION_PREFLIGHT.md).

| Дефект | Доказ і залишок |
| --- | --- |
| SA4-01 · High | Незалежний Sol security review коду `4cbaa6e3ccce628f8b7a27d8d6a85d9975973689` — PASS. 8 профільних тестів та ізольований старт застосунку підтвердили відмову за відсутнього, резервного або закороткого ключа і непідтримуваного алгоритму. Вхідні значення приховано. З явними ключами HS256/384/512 і з вимкненим Platform Admin штатний JWT flow пройшов. |
| SA4-02 · Medium | Пройшли regression tests приватності пошуку, курсора, помилок та проксі. Ізольований HTTP smoke підтвердив, що синтетичний маркер відсутній у відповіді та журналі Uvicorn. Журнали керованого проксі потрібно перевірити на цільовому staging. |
| SA4-03 · Medium | Ізольований API з окремою non-superuser роллю прочитав grants, підписки та 7/30-денні агрегати і зберіг аудит. Прямий `SELECT` клієнтських ролей відхилено для п’яти захищених таблиць. Фактичну роль підключення майбутнього staging потрібно перевірити окремо. |

## Докази перевірок

- **57 passed** для startup, search privacy, endpoint inventory і subscription status. [CI коду виправлень](https://github.com/eNgine9r/sellora/actions/runs/43226872281) також включає PostgreSQL та desktop/mobile Playwright.
- **PASS** для `npm run build` та HTTP smoke через зібраний Next.js до окремого Uvicorn і PostgreSQL 16.15 на Alembic head `202611120057`. Використано синтетичні записи.
- **PASS** для off-switch rollback. Після перезапуску API шість запитів до Platform Admin від admin і OWNER повернули `404`. CRM-вхід, `/auth/me` і читання підписки OWNER повернули `200`. Кількість grants, записів аудиту, usage, підписок і платіжних квитанцій та версія Alembic збереглися.

## Фактичний результат захищеного staging

- [Frontend](https://sellora-platform-staging.vercel.app/platform-admin) і [API](https://sellora-platform-staging-api.vercel.app/api/v1) підтверджені як `READY` у Vercel. Frontend deployment `dpl_37GwpwUN4CBnqGFxUWuDAW4jbWv8` зібраний з `1ac522b5`, API deployment `dpl_BVB2TyBz9NBhP2fvQymwHGW8uyfJ` — з `3e0763e9`. Докази TLS, ізольованого PostgreSQL, прав ролі та smoke задокументовано у [PR #417](https://github.com/eNgine9r/sellora/pull/417).
- 13.11.2026 власник вручну ввійшов і перевірив панель. Запит лише на читання до staging БД підтвердив активну роль `PLATFORM_ADMIN`, успішний вхід і дозволену операцію в аудиті.
- Для перевіреного дерева коду пройшло [8 із 8 завдань CI](https://github.com/eNgine9r/sellora/actions/runs/43230727857). Злитий коміт `8c3c2e7` має те саме дерево. Окремого запуску CI для merge-коміту GitHub не показав під час preflight.

Чеклісти нижче описують порядок підготовки й відкату. Зафіксовані вище результати стосуються окремого захищеного стенду.

## Staging rollout checklist

1. [ ] Погодити точний commit і прийняти #417. Зафіксувати результат Sol review для SA4-01. Повторити review, якщо зміниться перевірений код автентифікації або інший Critical/High fix. Отримати окремий дозвіл на staging rollout.
2. [ ] Підготувати окремі staging backend, PostgreSQL та захищену frontend-адресу. Перевірити за ідентичністю середовища, сервісу та БД, що маршрут не використовує бойовий Raspberry API або його базу. Використати синтетичні дані, окремі staging-ключі й облікові записи. Вимкнути інтеграційні записи, фонові обробники та виклики платіжних провайдерів.
3. [ ] Зафіксувати попередні сумісні frontend/backend артефакти, staging upstream і прапорці. За наявності даних перевірити відновлення резервної копії в одноразову БД. Перевірити Alembic head і застосовувати лише потрібні additive міграції до ідентифікованої staging БД.
4. [ ] Спочатку підняти backend із `SELLORA_PLATFORM_ADMIN_ENABLED=false` і `SELLORA_PRODUCT_USAGE_CAPTURE_ENABLED=false`. Підтвердити `/health` і commit. Для привілейованого режиму підготувати явний випадково згенерований `JWT_SECRET` належної довжини і штатну cookie session конфігурацію. При заміні ключа врахувати повторний вхід користувачів.
5. [ ] Зібрати відповідний frontend із `SELLORA_API_UPSTREAM_URL` для окремого staging API та перевірити same-origin HTTPS session. Узгодити пару API/UI, оскільки пошук і пагінація перейшли на POST. Зміни environment variables застосовуються в новому deployment. [Vercel](https://vercel.com/docs/environment-variables/managing-environment-variables)
6. [ ] Перевірити grants/RLS через реальне підключення staging-застосунку, включно з читанням синтетичних grants, підписок, usage та записом аудиту. Підтвердити відмову клієнтським ролям. Перед smoke увімкнути режим на окремому backend із grants лише для контрольних операторів. Writer увімкнути лише для синтетичної перевірки аналітики.
7. [ ] Перевірити anonymous `401`, workspace OWNER/MANAGER/ANALYST `403`, admin `200`, відсутність перетину даних між двома workspace, пошук, пагінацію і 7/30 днів. Перевірити синтетичний маркер у журналах проксі та API. Підтвердити `enforcement_enabled=false`, відсутність billing mutations і нормальну роботу CRM.
8. [ ] Записати результати у QA gate з commit, ідентифікаторами артефактів і статусами без секретів. Зберегти підтвердження rollback на цільовому staging перед рішенням про готовність.

## Rollback checklist

1. [ ] Якщо спостерігається витік, обхід прав, помилковий upstream, збій аудиту або регресія CRM, зупинити пілот і закрити staging-доступ.
2. [ ] У staging backend вимкнути `SELLORA_PLATFORM_ADMIN_ENABLED` і `SELLORA_PRODUCT_USAGE_CAPTURE_ENABLED`, перезапустити backend і дочекатися readiness. Перевірити, що platform routes повертають `404`, а CRM-сесії та tenant subscription read працюють.
3. [ ] Якщо вимкнення прапорців недостатньо, повернути зафіксовану сумісну пару frontend/backend із попереднім ізольованим staging upstream. Перевірити сумісність пари зі збереженим Alembic head перед перемиканням. Відкат схеми або видалення даних за цим сценарієм заборонені.
4. [ ] Повторити smoke для HTTPS, правильного upstream, сесій, tenant isolation і читання підписки. Звірити Alembic head та контрольні дані grants, audit, usage, підписок і платіжних квитанцій. Зберегти санітизовані докази та повернути статус **NO-GO** до усунення причини.

## Історичні умови перед staging rollout

Прийняття #417, ізольованість цільового staging, його фактична роль БД, журнали керованого проксі та відкат на цільових артефактах ще потребують підтвердження. Поточний публічний frontend використовує бойовий backend. Злиття в `main` може автоматично опублікувати frontend, тому момент злиття має входити в окремо погоджений rollout. [Налаштування Vercel у репозиторії](../../../frontend/vercel.json)
