# Sellora Platform Admin — production preflight

**13.11.2026 · NO-GO.** Ціль першого запуску — перегляд реальних магазинів, статусу підписки та активності. Готовність захищеного тестового стенду підтверджена в [handoff SA.5](handoffs/SA.5.md#фактичний-результат-захищеного-staging).

| Перевірка | Факт | Що потрібно для GO |
| --- | --- | --- |
| GitHub і кандидат | `main` на момент перевірки — `8c3c2e7`. На перевіреному ідентичному дереві пройшли [8/8 завдань CI](https://github.com/eNgine9r/sellora/actions/runs/43230727857). | Зафіксувати погоджені артефакти фронтенду й ARM64 backend та їхні SHA перед запуском. |
| Бойовий frontend | У підключеній команді Vercel знайдено три проєкти Sellora, усі зі staging-назвами. Спільний `sellora-web-staging` підтверджено на `a8e5ff2`. | Підтвердити бойову адресу та її поточний deployment, включно з upstream до Raspberry API. |
| Бойовий backend і БД | У нативному терміналі Raspberry підтверджено running image `sellora-backend:global-search-rpi-20261112`, commit `01a65098b78b478391be139d8781ff5ea068c108`, локальний readiness `200` і Alembic `202611120055`. Роль БД має `rolsuper=false` та `rolbypassrls=true`. | Підтвердити ACL фактичної ролі на схемі після міграцій і працездатність погодженого ARM64 образу. Зіставити публічний маршрут із підтвердженим локальним API. |
| Backup і rollback | Watchdog та три backup-таймери завантажені й активні. Docker image ID поточного backend зафіксований. Є [історичний owner handoff](../operations/s8-owner-release-handoff.md) і репетиція off switch на staging. | Підтвердити свіжий зашифрований backup і успішний restore в ізоляції. Перевірити, що фактична команда запуску попереднього backend сумісна з `202611120057`, та зафіксувати frontend для відкату. |
| Доступ оператора | Роль і password-session перевірені на staging. Застосування MFA чи погодженого еквівалента на бойовому маршруті не підтверджено. | Підтвердити захист входу на UI та API і видати окремий production grant погодженому оператору після рішення про запуск. [Roadmap](ROADMAP.md#sa5--security-review-та-staging-пілот) |

## Докази з Raspberry Pi та ізольованої БД

- 13.11.2026 нативний термінал показав image ID `sha256:126923f3c44e73df875358f96c1a9afd6e459428297a29b36ce081fd37df651e`. Git підтвердив `01a6509` як предка `8c3c2e7`. Два додані файли міграцій утворюють шлях `202611120055 → 202611120056 → 202611120057`.
- Таймери востаннє спрацювали 13.11.2026 за EET. Watchdog о 09:59:09, локальний DB backup о 06:34:19, Google Drive backup о 07:23:39, off-host encrypted backup о 07:09:07. Це часові мітки запуску таймерів. Для підтвердження backup потрібні докази завершення, цілісності артефакту та відновлення.
- На ізольованій PostgreSQL 16.15 із синтетичними даними міграції `055 → 056 → 057` пройшли. Репетиція перевірила читання й запис аудиту під non-superuser роллю з `BYPASSRLS` та явно наданими ACL, а також відсутність доступу клієнтських ролей. Окремо пройшли всі 7 тестів `test_platform_admin_postgres.py`. ACL і restore бойової БД потребують окремого підтвердження.
- У Git-версії `01a6509` стандартний `render-start.sh` викликає Alembic перед запуском API. Для відкату потрібно перевірити фактичну команду запуску Raspberry і виконати репетицію зі старим образом на цільовій схемі.

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

Для успішного відновлення потрібен окремий звіт з ізольованої БД. У звіті зафіксувати час створення backup, перевірку цілісності, ревізію відновленої схеми та результат перевірки застосунку. Паролі, ключі й архіви залишаються в операторському середовищі.

Після підтвердження всіх умов зафіксувати `GO` на конкретні артефакти. Окреме погодження потрібне перед бойовим deployment, міграціями або видачею production grant.
