# SA.0 → SA.1 — handoff

- **Репозиторій** `eNgine9r/sellora`
- **Перевірена база** `main` `ab4aa2a6dd8277797b71c25e6b6ea7323d73d041`
- **Наступний етап** SA.1 — Platform access foundation, модель SOL
- **Умова старту** злитий documentation PR SA.0 та окремий запуск SA.1

## Контекст для SA.1

Platform Admin має власний набір дозволів і окремий аудиторський журнал. Ідентичність використовує наявні активні користувацькі акаунти й серверні сесії. Tenant OWNER залишається роллю членства, `X-Workspace-ID` залишається tenant scope. Відомий крайовий випадок — legacy bearer може отримати `sid` через session upgrade, тому platform guard потребує підтвердженого походження сесії.

## Порядок виконання після старту

1. Звірити свіжий `main`, repo instructions, Alembic head, session login/upgrade/refresh, tenant authorization і [endpoint inventory](../../../backend/tests/security/test_endpoint_inventory.py). Перевірити, чи з'явився reusable platform-код після базового SHA.
2. Зафіксувати role matrix, DTO `/me`, вимоги до session provenance, bootstrap/revoke і транзакційний аудит із [архітектури](../ARCHITECTURE.md). Узгодити app-role/RLS шлях у disposable PostgreSQL і зберегти tenant login/upgrade compatibility.
3. Реалізувати тільки scope SA.1 за [roadmap](../ROADMAP.md). Додати окрему platform категорію в inventory, server guards і мінімальний shell. Перевірити відсутність tenant header та правильну ізоляцію кешу й logout.
4. Перед передачею зафіксувати evidence для role matrix, direct vs legacy-upgraded session, revoke, audit rollback, endpoint inventory, tenant regression, міграції в disposable PostgreSQL і доступу під фактичною DB role. Вказати, які перевірки лишилися staging-only. Оновити [STATUS.md](../STATUS.md).

## Рішення та відкриті залежності

| Тема | Власник наступного рішення |
| --- | --- |
| Походження сесій та cookie-session readiness | SA.1. Окремо перевірити staging config до ввімкнення privileged access |
| Політика покриття product events, retention і обробки втрат | SA.3. Уточнити за реальними producers і сценаріями видалення даних |
| Pilot trial і право на write-path | SA.4. Погодити eligibility, строки, reason codes, plan code та вимоги до свіжості входу |
| Security audit retention, відновлення доступу і privileged authentication перед production | SA.5. Затвердити з відповідальним за доступ |

## Перевірка SA.0

Звірено route/service/model/repository для workspace authorization, audit, subscription та receipts, frontend transport і shell, міграційний граф і канонічні regression suites. Перевірки SA.0 охоплюють зв'язність посилань, узгодженість stage contracts і diff з чотирьох Markdown-файлів. Це перевірка за джерельним кодом. Runtime, міграційна репетиція, staging та production поза її межами.
