# Sellora Platform Admin — production preflight

**13.11.2026 · Production NO-GO.** Захищений staging із MFA, перевірки PR #419 і репетиція відкату ARM64 на `202611130058` пройшли. Автоматичне призначення бойового домену вимкнено, код MFA злитий і новий frontend зібрано окремо. Бойовий rollout очікує відновлення свіжої копії, запуску нової пари frontend/API та реєстрації production-фактора. Ціль першого запуску — перегляд магазинів, статусу підписки та активності.

| Перевірка | Факт | Що потрібно для GO |
| --- | --- | --- |
| GitHub і кандидат | `main` — `be3c79f6995f3c10b94a50057415dceace5d40a0` після злиття #419. Дерево збігається з перевіреним `fbaebb3`. [CI після злиття](https://github.com/eNgine9r/sellora/actions/runs/43414778134) пройшов 8/8. | Зберегти зафіксовані SHA та image ID у релізному записі. |
| Бойовий frontend | [Робочий CRM](https://sellora-web-staging.vercel.app) обслуговує deployment `dpl_HbiuVq2Bv5D9JwJHyp7xxPg9KnL8` з `a8e5ff2`. Автопризначення домену вимкнено. Новий deployment `dpl_9G57Rp5NosKJWGwifELSPuzX4Udi` зі злитого `main` має `READY`. Бойовий домен лишився на попередньому deployment. | Після запуску нового API перевірити CRM-вхід і MFA на точній парі, тоді призначити бойовий домен. |
| Бойовий backend і БД | Через RDC підтверджено API `01a65098b78b478391be139d8781ff5ea068c108`, readiness `200`, нуль перезапусків, Alembic `202611120055`, cookie sessions увімкнені, Platform Admin вимкнений. | Перед бойовою міграцією підтвердити актуальну відновлювану копію й роль міграції. Після міграції до `058` звірити ACL та RLS, запис аудиту й звичайні CRM-операції. |
| Backup і rollback | Архів з `055` відновлено в ізоляції. На Raspberry перевірено запуск кандидата і сумісного образу відкату на синтетичній `058`. Новий архів `sellora-db-20261113-110634.pgdump.enc` підтверджено на резервному вузлі о `11:06:58 UTC`. | Виконати контрольне відновлення нового архіву в нативному терміналі власника перед міграцією. |
| Доступ оператора | Захищений staging вимагає MFA. Власник підтвердив `MFA_LOGIN=PASS`. Аудит зафіксував вхід і читання списку магазинів. | Налаштувати окремий production-ключ MFA та зареєструвати фактор погодженого оператора. Перевірити прямий API, звичайний CRM-вхід і закриття доступу перемикачем. |

## Перевірка MFA

Оглянуто [PR #419](https://github.com/eNgine9r/sellora/pull/419) від `8c3c2e7` до `fbaebb3`, а також окреме пакування захищеного staging `eb80371`. У перевірених змінах не підтверджено дефектів Critical або High.

- Усі платформні читання проходять перевірку password-session, активного grant, потрібного дозволу й MFA. Підтвердження має строк дії 30 хвилин, зберігається як SHA-256 і перевіряється щодо користувача, сесії та часу видачі grant. Logout, відкликання або повторна видача grant і заміна фактора скасовують попередній доступ. Перевірка звичайного CRM JWT зберегла чинний контракт.
- TOTP приймається один раз. Сервер блокує рядок фактора на час перевірки та фіксує успішну перевірку, останній прийнятий крок і аудит в одній транзакції. П’ять невдалих спроб обмежують повторні спроби протягом п’яти хвилин. Невдалі спроби мають лічильник, а аудит перевірки фіксує успіх. Це залишає обмежену видимість тимчасових блокувань оператора.
- Синтетичні тести підтвердили відмову без сесії, для tenant OWNER, після відкликання сесії чи grant, після строку дії MFA, у разі повтору TOTP та перевищення ліміту спроб. У захищеному staging підтверджено `401` для прямого запиту без сесії, успішний MFA та читання списку магазинів. Повторно пройшли 60 тестів `tests/security` на окремій PostgreSQL.
- Заміна та видалення фактора очищають попередні підтвердження в тій самій транзакції. Автоматизований тест видалення перевіряє наступну спробу MFA. Окреме підтвердження, видане безпосередньо перед заміною чи видаленням, не охоплено цим тестом. За втрати пристрою відкликати grant і замінити або видалити фактор.
- TOTP передається в тілі POST. Backend приховує приватні значення в помилках валідації та у своєму access log. Staging-проксі передає query до API, тому випадково доданий у URL секрет може потрапити у журнали перед backend. Перевірка живих журналів усіх проміжних сервісів із контрольним значенням залишається відкритою. TOTP також зберігає ризик фішингу. [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html)

## Порядок бойового запуску

1. Автопризначення бойового домену в Vercel вимкнено. PR #419 злитий. Deployment зі злитого `main` має `READY` і окрему адресу. Прямі перевірки цієї збірки повернули `200` для `/login` і `/platform-admin`, `401` для анонімного `/api/v1/auth/me`, `404` для вимкненого `/api/v1/platform-admin/me`. Бойовий домен і далі вказує на `dpl_HbiuVq2Bv5D9JwJHyp7xxPg9KnL8`. [Vercel](https://vercel.com/docs/deployments/promoting-a-deployment)
2. На Raspberry виправлено застарілий image ID у плані watchdog під його lock. Наступний запуск сервісу пройшов, readiness `200`, перезапусків немає. Під час rollout оновлювати ціль watchdog разом із фактичним образом і так само при відкаті. Звичайне підключення Raspberry до Supabase використовує TLS. Окремий read-only запит пройшов з `verify-full` і CA Supabase. Режим чинної конфігурації підключення не змінювався.
3. У погоджене вікно отримати `restore_check=PASS` для свіжого архіву в нативному терміналі власника, потім застосувати `055 → 056 → 057 → 058` через погоджену роль. Підтвердити нову ревізію, RLS і дозволи на платформні таблиці та аудит. Запустити кандидат із `SELLORA_PLATFORM_ADMIN_ENABLED=false` і перевірити CRM, cookie login, замовлення та підписку. Зберегти вимкнені зміни enforcement і платежів.
4. Для активації Platform Admin перевірити `ENVIRONMENT=production`, явно встановити `SELLORA_PLATFORM_ADMIN_MFA_REQUIRED=true`, зберегти окремий production Fernet-ключ і зареєструвати фактор погодженого оператора. Увімкнути адмінпанель після перевірки production frontend/API та відповідних доступів. Після перевірки пари призначити бойовий домен у Vercel вручну. Перевірити прямий API, успішний MFA, аудит, відмову без MFA та для CRM OWNER.
5. За збою вимкнути Platform Admin і повернути підтверджений frontend та сумісний ARM64 rollback-образ. Залишити БД на `058` зі збереженням MFA і аудиту. Повторити CRM smoke й перевірити `404` для Platform Admin. Образ старого бойового контейнера має packaged head `055` і для відкату на `058` непридатний.

### Перевірка свіжої резервної копії

У нативному терміналі `btcradar@btc-radar` запустити підготовлену копію скрипта:

```bash
bash /home/btcradar/sellora-mfa-qa.Kr2o1qzq/release-restore-check.sh
```

Скрипт звіряє SHA-256 архіву з off-host квитанцією і відновлює БД у контейнері без мережі. Очікуваний результат `restore_check=PASS`. Спроба з RDC зупинилася на `OWNER_TERMINAL_REQUIRED`, до відновлення даних.

## Докази з Raspberry Pi та ізольованої БД

- 13.11.2026 нативний термінал показав image ID `sha256:126923f3c44e73df875358f96c1a9afd6e459428297a29b36ce081fd37df651e`. Git підтвердив `01a6509` як предка `8c3c2e7`. Два додані файли міграцій утворюють шлях `202611120055 → 202611120056 → 202611120057`.
- Таймери востаннє спрацювали 13.11.2026 за EET. Watchdog о 09:59:09, локальний DB backup о 06:34:19, Google Drive backup о 07:23:39, off-host encrypted backup о 07:09:07. Це часові мітки запуску таймерів. Для підтвердження backup потрібні докази завершення, цілісності артефакту та відновлення.
- На ізольованій PostgreSQL 16.15 із синтетичними даними міграції `055 → 056 → 057` пройшли. Репетиція перевірила читання й запис аудиту під non-superuser роллю з `BYPASSRLS` та явно наданими ACL, а також відсутність доступу клієнтських ролей. Окремо пройшли всі 7 тестів `test_platform_admin_postgres.py`. ACL бойової ролі ще потрібно підтвердити.
- У Git-версії `01a6509` стандартний `render-start.sh` викликає Alembic перед запуском API. Для відкату потрібно перевірити фактичну команду запуску Raspberry і виконати репетицію зі старим образом на цільовій схемі.

## Результат backup-сервісів

У нативному терміналі 13.11.2026 підтверджено `LoadState=loaded`, `Result=success` і `ExecMainStatus=0` для трьох сервісів.

| Сервіс | Старт EET | Завершення EET |
| --- | --- | --- |
| `sellora-db-backup.service` | 06:34:19 | 06:34:47 |
| `sellora-google-drive-backup.service` | 07:23:39 | 07:23:53 |
| `sellora-offhost-encrypted-backup.service` | 07:09:07 | 07:09:11 |

Власник передав санітизований огляд джерел. Локальний сервіс створює зашифрований OpenSSL архів PostgreSQL у custom format і перевіряє його каталог через `pg_restore -l`. Off-host сервіс отримує від віддаленого вузла підтвердження SHA-256 та записує локальну квитанцію з назвою, розміром і SHA-256 архіву.

У нативному терміналі власника запустити [репетицію відновлення](../../deploy/raspberry/sellora_sa_restore_check.sh) з цієї гілки:

```bash
bash deploy/raspberry/sellora_sa_restore_check.sh
```

Скрипт звіряє локальну зашифровану копію з off-host квитанцією та відновлює архів у контейнері PostgreSQL 17 без мережі з файловою системою БД у tmpfs. Він перевіряє ревізію `202611120055` і доступність ключових таблиць. Артефакт, ключі й розшифрований вміст залишаються на Raspberry Pi.

Попередні спроби виявили конфлікт створення `public` (`42P06`) та відмову під час `COPY` (`22021`). Скрипт очищає об’єкти з архіву лише в тимчасовій БД в одній транзакції та явно встановлює UTF-8.

### Результат контрольного відновлення

**PASS · 13.11.2026.** Власник виконав скрипт із коміту `a588957e9d0eba4a7e52f206687b2dc4f9672b24` на Raspberry Pi. Архів `sellora-db-20261113-043419.pgdump.enc` відповідав off-host квитанції від `2026-11-13T05:09:11Z`. Тимчасова БД підтвердила `UTF8`, відновлену ревізію `202611120055` і доступність таблиць users, workspaces, orders та workspace_subscriptions. Образ PostgreSQL `sha256:18cfe3ef5e6815560c98237d6216d1e5119702fb0f3894c8785dd58b8bbe5d73`.

Перевірено відновлення локального архіву, ідентичність якого підтверджує off-host квитанція. Окреме завантаження віддаленої копії, ACL бойової ролі та запуск попереднього образу API після міграції до `202611120057` залишаються поза цим результатом.

## Повторна перевірка на Raspberry Pi

З нативного термінала власника отримати факти про поточний контейнер і БД. Назва контейнера, порт і список таймерів взяті з [owner handoff](../operations/s8-owner-release-handoff.md). Якщо вони змінилися, зафіксувати розбіжність і звірити їх з актуальною конфігурацією.

```bash
docker inspect --format 'image={{.Config.Image}} id={{.Image}} status={{.State.Status}}' sellora-rpi-backend-1
curl -fsS --max-time 8 http://127.0.0.1:18000/health | python3 -c 'import json,sys; d=json.load(sys.stdin); print("status", d.get("status"), "commit", d.get("runtime_commit"))'
curl -sS --max-time 8 -o /dev/null -w 'readiness=%{http_code}\n' http://127.0.0.1:18000/health/ready
docker exec -i --workdir /app sellora-rpi-backend-1 python - <<'PY'
from sqlalchemy import text
from app.database.session import engine

try:
    with engine.begin() as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))
        conn.execute(text("SET LOCAL statement_timeout = '5s'"))
        print("alembic", conn.execute(text("SELECT version_num FROM public.alembic_version")).scalars().all())
        role = conn.execute(text(
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
        )).one()
        print("db_superuser", role[0], "db_bypassrls", role[1])
except Exception as exc:
    raise SystemExit(f"DB preflight failed: {type(exc).__name__}") from None
PY
systemctl --user show --no-pager -p Id -p LoadState -p ActiveState -p LastTriggerUSec \
  sellora-runtime-health-watchdog.timer sellora-db-backup.timer \
  sellora-google-drive-backup.timer sellora-offhost-encrypted-backup.timer
```

Передати лише результат цих перевірок. Статус таймера підтверджує його стан і останній запуск. Результати відповідних сервісів можна отримати без запуску нового backup:

```bash
systemctl --user show --no-pager -p Id -p LoadState -p Result -p ExecMainStatus \
  -p ExecMainStartTimestamp -p ExecMainExitTimestamp \
  sellora-db-backup.service sellora-google-drive-backup.service \
  sellora-offhost-encrypted-backup.service
```

## Наступна перевірка для відкату

Попередній огляд повернув `startup_mode=owner_review_required`. Історичний [Raspberry handoff](../operations/s8-owner-release-handoff.md) описує обгортку `scripts/start_raspberry.py`. Вона не входить у Git-версію бойового коміту. Потрібно звірити, чи її використовує саме поточний контейнер.

У нативному терміналі власника виконати огляд метаданих Docker і фіксованих файлів контейнера. Вивід містить лише відомі типи запуску, SHA-256 обгортки, ознаки в її тексті та наявність файлів ревізій.

```bash
(
  set -e -o pipefail
  container=sellora-rpi-backend-1
  docker inspect --format '{{json .Path}} {{json .Args}}' "$container" |
    python3 -c '
import json, re, sys
raw = sys.stdin.read().strip()
path, end = json.JSONDecoder().raw_decode(raw)
command = " ".join([path, *json.loads(raw[end:].strip())])
for pattern, label in (
    (r"\bstart_raspberry\.py\b", "raspberry_wrapper"),
    (r"\brender-start\.sh\b|\balembic\b", "migration_script_or_command"),
    (r"\buvicorn\b", "uvicorn_observed"),
):
    if re.search(pattern, command):
        print("startup_mode=" + label)
        break
else:
    print("startup_mode=owner_review_required")
'
  docker exec -i --workdir /app "$container" python -IB - <<'PY'
import hashlib
import re
from pathlib import Path

wrapper = Path('/app/scripts/start_raspberry.py')
if wrapper.is_file() and wrapper.stat().st_size <= 65536:
    source = wrapper.read_bytes()
    print('wrapper_sha256=' + hashlib.sha256(source).hexdigest())
    for marker in ('alembic', 'uvicorn'):
        present = bool(re.search(rb'\b' + marker.encode() + rb'\b', source))
        print(f'wrapper_{marker}_reference={"yes" if present else "no"}')
else:
    print('wrapper_source=unavailable')

versions = Path('/app/alembic/versions')
for suffix in ('055', '056', '057'):
    matches = any(versions.glob(f'202611120{suffix}_*.py'))
    print(f'packaged_revision_{suffix}={"yes" if matches else "no"}')
PY
)
```

### Результат локальної репетиції відкату

- Власник підтвердив у поточному контейнері наявність файлу `055`, відсутність `056/057` і згадки Alembic та Uvicorn у тексті `start_raspberry.py`. Самі згадки залишають відкритим питання, як саме обгортка викликає Alembic.
- На ізольованій PostgreSQL старий код з коміту `01a6509` повернув `Can't locate revision identified by '202611120057'` під час `alembic upgrade head`. При прямому старті застосунку з вимкненим Meta-воркером пройшли readiness та перевірка анонімних маршрутів. Ревізія залишилася `057`.
- У тимчасовий checkout старого коду додано тільки точні файли міграцій `056/057` з release candidate. На синтетичній БД з чинною `057` пройшли `alembic upgrade head`, readiness, вхід через cookie session, читання workspace і підписки з `enforcement_enabled=false`. Маршрут Platform Admin повернув `404`. Ця репетиція використала локальне середовище Python, без запуску фактичного ARM64 образу чи копії production.

### Репетиція ARM64 через RDC

У бойовій обгортці `scripts/start_raspberry.py` підтверджено звірку packaged head з фактичною ревізією БД перед запуском Uvicorn. SHA-256 обгортки `4e0c676b29aaac5312f51e7d06ef5e8ff7cb0faee6d396215b39d22a47614600`. На ізольованій `057` оригінальний образ повернув `DATABASE_SCHEMA_MISMATCH`.

| Артефакт | ARM64 image ID |
| --- | --- |
| Відкат, старий CRM-код із міграціями `056/057` | `sha256:7260995555c5278b33771cb4ad9811331e235f10371bf5f19205834964f646d3` |
| Кандидат `8c3c2e7` | `sha256:f78d6467318454d296915f30f7ec7b1d8d9f26a0792cf5eb9193fda91a33b11e` |

Обидва образи зібрано як похідні від зафіксованого бойового образу. Образ відкату додає два файли міграцій. Кандидат накладає 28 змінених шляхів у backend і `RELEASE_REVISION`. Для 28 шляхів звірено хеші в базовому образі з `01a6509` і в кандидаті з `8c3c2e7`. Перевірка обмежена зміненими шляхами.

На PostgreSQL 17 із синтетичними даними міграції `055 → 056 → 057` пройшли. Обидва образи запустилися через фактичну обгортку та пройшли readiness, cookie login, читання магазинів і підписок з `enforcement_enabled=false`. Кандидат повернув `401` без сесії, `403` для власника магазину і `200` для оператора. Використано тестову роль із `BYPASSRLS` та явно наданими ACL.

Послідовність кандидат → кандидат з вимкненим Platform Admin → образ відкату завершилася `OFFSWITCH_AND_ROLLBACK_PRESERVE_DB_PASS`. Після вимкнення й відкату Platform Admin повертав `404`, CRM smoke проходив, ревізія та контрольні кількості записів grants, аудиту, активності, підписок і платіжних квитанцій збігалися. Кандидат створив записи аудиту під час дозволених запитів. Після тесту тимчасові контейнери прибрано.

Маршрут Tailscale `/api/v1` веде до бойового Raspberry API. Його ідентичність підтверджує `/sellora-health`. Після репетиції бойовий образ залишався healthy з нульовим лічильником перезапусків, БД залишалася на `055`.

### Репетиція ARM64 з MFA на `058`

| Артефакт | ARM64 image ID |
| --- | --- |
| Кандидат `fbaebb3` | `sha256:16748002cf768916d984ab64131cd10da85f8abe9900cc66f5ccfe6b674ad5c7` |
| Відкат `01a6509` з файлами міграцій до `058` | `sha256:c1707364bff4cc3c4b21af33d59bf86a56cb48c0e86bb669d90c4f7c9eeeb917` |

У PostgreSQL 17 із синтетичними даними роль без superuser із `BYPASSRLS` і володінням таблицями успішно застосувала `055 → 058`. Обидва образи запущено фактичною Raspberry-обгорткою. Кандидат пропустив оператора з MFA, відхилив tenant OWNER та повтор TOTP. Після вимкнення Platform Admin і переходу на rollback пройшли readiness, cookie login, список магазинів і читання підписки з `enforcement_enabled=false`. На rollback Platform Admin повернув `404`, БД зберегла ревізію `058`, фактор та запис успішного MFA. Результат RDC — `ARM64_MFA_ROLLBACK_058=PASS`. Бойовий образ та БД залишилися на `01a6509` і `055`.

Після підтвердження відновлення, перевірки точної пари frontend/API та реєстрації production-фактора зафіксувати `GO` для конкретних артефактів.
