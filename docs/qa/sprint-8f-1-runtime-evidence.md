# Sprint 8F.1 Runtime Evidence

Status: **pending external runtime validation**.

This repository change does not contain secrets, customer PII, runtime credentials, sender refs, provider payloads, or real TTN data.

## Evidence checklist

- [ ] Merge commit SHA deployed to Render.
- [ ] Backend `/health` returns `200` and the expected runtime commit.
- [ ] Packaged Alembic head equals `202607180025`.
- [ ] Runtime database revision equals `202607180025`.
- [ ] Vercel deployment is Ready for the same merge commit.
- [ ] Environment Nova Poshta writes disabled before smoke test.
- [ ] Workspace provider permission disabled before smoke test.
- [ ] Effective provider writes disabled after cleanup.

## Current repository evidence

- New migration head: `202607180025`.
- Runtime/provider evidence: not available in the local Codex environment.
