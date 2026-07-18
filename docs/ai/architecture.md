# AI architecture

The backend AI module lives under `backend/app/ai/` and separates provider abstraction, prompt registry, structured output schemas, and orchestration services. Business services call `AIGatewayService`; provider SDK details must not leak into CRM workflows or API routes.

Direct data is workspace-scoped through canonical Direct and AI tables. AI suggestions and action drafts are human-review artifacts, not autonomous mutations.
