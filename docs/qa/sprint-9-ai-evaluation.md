# Sprint 9 AI evaluation

Deterministic evaluation cases are stored in `backend/tests/fixtures/ai/direct_intelligence_cases.json`. Default backend tests use schema validation and fake/provider-independent behavior; live provider calls are opt-in only.

Metrics tracked for the sprint include intent accuracy, entity extraction precision/recall, structured output validity, product match accuracy, false product match rate, clarification correctness, unsafe action rate, latency, tokens, and estimated cost.
