# Sellora Platform Admin — production preflight

**13.11.2026 · NO-GO.** Ціль першого запуску — перегляд реальних магазинів, статусу підписки та активності. Готовність захищеного тестового стенду підтверджена в [handoff SA.5](handoffs/SA.5.md#фактичний-результат-захищеного-staging).

| Перевірка | Факт | Що потрібно для GO |
| --- | --- | --- |
| GitHub і кандидат | `main` на момент перевірки — `8c3c2e7`. На перевіреному ідентичному дереві пройшли [8/8 завдань CI](https://github.com/eNgine9r/sellora/actions/runs/43230727857). ARM64 кандидат і rollback зібрані на Raspberry. | Погодити перевірені артефакти для релізу й production-конфігурацію фронтенду. |
| Бойовий frontend | Власник підтвердив [sellora-web-staging.vercel.app](https://sellora-web-staging.vercel.app) як адресу CRM для реальних магазинів. Vercel показує `READY`, коміт `a8e5ff2`, deployment `dpl_HbiuVq2Bv5D9JwJHyp7xxPg9KnL8`. Frontend дерева `8c3c2e7` зібрано локально з тестовим upstream. | Перевірити нову збірку з відповідним API і захистом доступу та зафіксувати сумісний frontend для відкату. Поточний deployment збережено як точку відліку. |
| Бойовий backend і БД | Raspberry і публічний `/sellora-health` підтверджують commit `01a6509`. Бойова БД на `202611120055`. Роль має `rolsuper=false`, `rolbypassrls=true`, `USAGE/CREATE` на схемі й володіє users, workspaces, auth_sessions та alembic_version. | Підтвердити права на нові таблиці та запис аудиту в production-перевірці після погоджених міграцій. |
| Backup і rollback | Архів відновлено в ізоляції. Оригінальний ARM64 образ відхиляє `057`, сумісний ARM64 образ відкату стартує на `057` і проходить CRM smoke. | Погодити пару frontend/backend для відкату та перевірити актуальність копії перед релізом. |
| Доступ оператора | Кандидат вимагає password-session і роль оператора. MFA для Platform Admin у цьому коді відсутня. Бойовий API доступний через публічний Funnel. | Реалізувати та перевірити MFA для операторів або погодити еквівалент, який захищає також прямий доступ до API. Видати production grant після рішення про запуск. [Roadmap](ROADMAP.md#sa5--security-review-та-staging-пілот) |

## Робочий маршрут і захист оператора

- `/login` робочого Vercel-фронтенду повернув `200`. На Vercel, публічному Raspberry API та локальному контейнері через RDC звірено однакові коди й SHA-256 тіл відповідей для `/auth/me` (`401`) та `/platform-admin/me` (`404`). Tailscale на Raspberry підтверджує проксі `/api/v1` на локальний порт `18000`, а `/sellora-health` публічно й локально показує `01a6509`. Це перевірка поточної пари без сесії. Нову пару ще потрібно перевірити з входом у браузері.
- Публічний Funnel не надає ідентифікацію оператора. Захист сторінки у Vercel сам по собі не поширюється на прямий доступ до Raspberry API. Права Platform Admin мають перевірятися на backend за кожним запитом. [Tailscale Serve та identity headers](https://tailscale.com/docs/features/tailscale-serve) · [OWASP MFA](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html)
- Запропонований варіант — MFA для операторів із серверною перевіркою статусу сесії у platform guard. На захищеному staging перевірити відмову для оператора лише з паролем, відмову для tenant OWNER, успішний доступ оператора після MFA, поведінку refresh і revoke, а також прямий API. Вхід звичайних користувачів CRM має пройти регресійні перевірки.

Після staging перевірок зафіксувати нову пару frontend/API, сумісну пару для відкату й підтвердження backup. У погоджене вікно релізу застосувати міграції, перевірити права на нові таблиці, підтвердити звичайний CRM-вхід і лише тоді відкрити Platform Admin для погодженого оператора. У разі збою закрити Platform Admin і використати перевірений відкат зі збереженням ревізії `057`.

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

Після підтвердження всіх умов зафіксувати `GO` на конкретні артефакти. Окреме погодження потрібне перед бойовим deployment, міграціями або видачею production grant.
