# Sellora Platform Admin — production preflight

**13.11.2026 · NO-GO.** Ціль першого запуску — перегляд реальних магазинів, статусу підписки та активності. Готовність захищеного тестового стенду підтверджена в [handoff SA.5](handoffs/SA.5.md#фактичний-результат-захищеного-staging).

| Перевірка | Факт | Що потрібно для GO |
| --- | --- | --- |
| GitHub і кандидат | `main` на момент перевірки — `8c3c2e7`. На перевіреному ідентичному дереві пройшли [8/8 завдань CI](https://github.com/eNgine9r/sellora/actions/runs/43230727857). | Зафіксувати погоджені артефакти фронтенду й ARM64 backend та їхні SHA перед запуском. |
| Бойовий frontend | У підключеній команді Vercel знайдено три проєкти Sellora, усі зі staging-назвами. Спільний `sellora-web-staging` підтверджено на `a8e5ff2`. | Підтвердити бойову адресу та її поточний deployment, включно з upstream до Raspberry API. |
| Бойовий backend і БД | Raspberry Pi online у Commander. Запити до публічної адреси API повертали тайм-аути та `404`, без достовірної ідентифікації запущеного коміту. Команда перевірки watchdog через Commander відхилена з `READ_POLICY_SERVICE_NOT_ALLOWED`. | Отримати з нативного термінала власника поточні образ і коміт, loopback readiness, Alembic revision та ознаки ролі БД. Перевірити міграційний шлях і видимість Platform Admin під реальною app role в ізольованому середовищі. |
| Backup і rollback | Є [історичний owner handoff для Raspberry](../operations/s8-owner-release-handoff.md) і репетиція off switch на staging. Актуальний зашифрований backup, результат контрольного restore та сумісність бойового rollback із цільовою схемою не підтверджені. | Підтвердити актуальність backup, виконати перевірку відновлення в ізольованій БД та зафіксувати попередню пару образів і сумісний порядок відкату. |
| Доступ оператора | Роль і password-session перевірені на staging. Застосування MFA чи погодженого еквівалента на бойовому маршруті не підтверджено. | Підтвердити захист входу на UI та API і видати окремий production grant погодженому оператору після рішення про запуск. [Roadmap](ROADMAP.md#sa5--security-review-та-staging-пілот) |

## Наступна перевірка на Raspberry Pi

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

Передати лише результат цих перевірок. Статус таймера підтверджує його стан і останній запуск, а успішне відновлення потрібно підтвердити окремим звітом з ізольованої БД.

Після підтвердження всіх умов зафіксувати `GO` на конкретні артефакти. Окреме погодження потрібне перед бойовим deployment, міграціями або видачею production grant.
