# Sellora Platform Admin — production preflight

**13.11.2026 · NO-GO.** Ціль першого запуску — перегляд реальних магазинів, статусу підписки та активності. Готовність захищеного тестового стенду підтверджена в [handoff SA.5](handoffs/SA.5.md#фактичний-результат-захищеного-staging).

| Перевірка | Факт | Що потрібно для GO |
| --- | --- | --- |
| GitHub і кандидат | `main` на момент перевірки — `8c3c2e7`. На перевіреному ідентичному дереві пройшли [8/8 завдань CI](https://github.com/eNgine9r/sellora/actions/runs/43230727857). | Зафіксувати погоджені артефакти фронтенду й ARM64 backend та їхні SHA перед запуском. |
| Бойовий frontend | У підключеній команді Vercel знайдено три проєкти Sellora, усі зі staging-назвами. Спільний `sellora-web-staging` підтверджено на `a8e5ff2`. | Підтвердити бойову адресу та її поточний deployment, включно з upstream до Raspberry API. |
| Бойовий backend і БД | У нативному терміналі Raspberry підтверджено running image `sellora-backend:global-search-rpi-20261112`, commit `01a65098b78b478391be139d8781ff5ea068c108`, локальний readiness `200` і Alembic `202611120055`. Роль БД має `rolsuper=false` та `rolbypassrls=true`. | Підтвердити ACL фактичної ролі на схемі після міграцій і працездатність погодженого ARM64 образу. Зіставити публічний маршрут із підтвердженим локальним API. |
| Backup і rollback | Усі три backup-сервіси завершилися успішно. Локальний зашифрований архів, хеш якого відповідає off-host квитанції, відновлено в ізольованій БД до `202611120055`. На staging пройшла репетиція off switch. | Перевірити запуск попереднього backend із фактичною командою Raspberry на `202611120057` та зафіксувати frontend для відкату. Перед релізом підтвердити актуальність копії. |
| Доступ оператора | Роль і password-session перевірені на staging. Застосування MFA чи погодженого еквівалента на бойовому маршруті не підтверджено. | Підтвердити захист входу на UI та API і видати окремий production grant погодженому оператору після рішення про запуск. [Roadmap](ROADMAP.md#sa5--security-review-та-staging-пілот) |

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

У нативному терміналі власника визначити спосіб запуску бойового контейнера. Команда виводить лише тип запуску, без аргументів і змінних середовища.

```bash
docker inspect --format '{{json .Path}} {{json .Args}}' sellora-rpi-backend-1 |
  python3 -c '
import json, re, sys
raw = sys.stdin.read().strip()
path, end = json.JSONDecoder().raw_decode(raw)
argv = json.loads(raw[end:].strip())
command = " ".join([path, *argv])
if re.search(r"\brender-start\.sh\b|\balembic\b", command):
    print("startup_mode=migration_script_or_command")
elif re.search(r"\buvicorn\b", command):
    print("startup_mode=uvicorn_observed")
else:
    print("startup_mode=owner_review_required")
'
```

Визначений тип запуску слугує для підготовки репетиції. Для підтвердження відкату потрібно запустити зафіксований попередній образ на ізольованій схемі `202611120057` з погодженою конфігурацією й перевірити readiness та базові CRM-операції.

Після підтвердження всіх умов зафіксувати `GO` на конкретні артефакти. Окреме погодження потрібне перед бойовим deployment, міграціями або видачею production grant.
