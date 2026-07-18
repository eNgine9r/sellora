# AI provider configuration

Credentials are stored only in platform secrets/environment variables. Do not store AI API keys in PostgreSQL, frontend code, browser storage, cookies, API responses, logs, or audit metadata.

Supported variables: `AI_PROVIDER`, `AI_API_KEY`, `AI_DEFAULT_MODEL`, `AI_FAST_MODEL`, `AI_REQUEST_TIMEOUT_SECONDS`, `AI_MAX_RETRIES`, `AI_MAX_INPUT_CHARACTERS`, `AI_DEFAULT_DAILY_TOKEN_LIMIT`, `AI_DEFAULT_MONTHLY_BUDGET_USD`, `AI_FEATURE_ENABLED`.

`/api/v1/ai/health` returns only safe booleans and provider selection metadata; it never performs a paid provider request.
