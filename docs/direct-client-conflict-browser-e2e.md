# S2-QA — Direct client-conflict browser coverage

Refs [#360](https://github.com/eNgine9r/sellora/issues/360). The existing component VM
test and API tests remain useful, but they do not establish browser E2E acceptance.
This separate CI job runs the actual `/login` and `/direct` pages, the real same-origin
Next API rewrite, a normal authenticated FastAPI process and disposable PostgreSQL.
Issue closure requires successful browser results at the reviewed commit.

## Coverage inventory

Each scenario runs in Chromium at desktop 1440×1000 and mobile 390×844. Mobile tests
open the actual client-details disclosure before using the identity controls.

| Scenario | Browser action and API observation | Independent committed-state check |
| --- | --- | --- |
| Confirm | Request prospect creation, receive a real 409 for two matching customers, choose the named second candidate, explicitly confirm, reload | Exactly the chosen binding and one reviewed audit event; customer identities unchanged |
| Cancel | Provoke the same conflict, choose a candidate, cancel and reload; no link request is sent | No binding, customer edit or identity-link audit |
| Tenant denial | Foreign customer ID, foreign conversation ID and unauthorized workspace header are submitted by authenticated browser requests | 409/404/403, no foreign identity disclosure, no binding or customer edits |

The fixture creates distinct cases, two workspaces and two ordinary manager users.
Every case has two matching local customers and one matching foreign customer. No
real customer data, messages, orders, shipments, TTNs or provider credentials are used.
Confirmation is verified again after a full browser reload, and the CLI inspects
PostgreSQL through a separate connection so a local React cache cannot satisfy it.
The tests also check that no messages, leads, orders or shipments were created.

## Harness boundary

`backend/scripts/direct_client_conflict_e2e.py` is a CLI only. It is not imported by
FastAPI and publishes no seed, mock, test-auth or QA endpoint. It refuses to connect
unless all of these conditions hold:

- `SELLORA_DIRECT_CONFLICT_E2E=YES`;
- PostgreSQL, loopback host, exact database name
  `sellora_direct_client_conflict_e2e_isolated`;
- External workers, sending, syncing, AI and provider writes explicitly disabled.

Seeding additionally requires current Alembic head and no application data. It creates
random synthetic credentials in a newly created 0600 manifest and refuses overwrites.
That manifest is never uploaded as an artifact and CI removes it after the run.

The Playwright configuration starts only loopback servers on ports 3100 and 8100 and
refuses to reuse an already running service. Login uses the existing cookie-session
API; no token is forged and no dependency override is installed. External processing
and sending are disabled, provider upstreams point at a closed loopback port, browser
network access is restricted to the local frontend, and API responses are never mocked.
Traces are disabled to avoid retaining synthetic login tokens; failure screenshots and
the explicit-confirmation screenshot contain synthetic UI data only.

## Run and assess

The `direct-client-conflict-e2e` CI job provisions PostgreSQL 16, installs the exact
Playwright dev dependency and Chromium, migrates the empty database, seeds it and runs
`npm run test:e2e:direct-identity` from `frontend`. The database and servers are local
to that job; this does not deploy or contact staging/production. Existing CI checks
remain unchanged. Failure artifacts are retained for seven days.

For local use, provide a fresh loopback PostgreSQL database with the exact name above,
set `DATABASE_URL`, `SELLORA_DIRECT_CONFLICT_E2E=YES`, a private absolute
`SELLORA_DIRECT_CONFLICT_MANIFEST` path, `PYTHONPATH=.` and every flag listed in the CLI's
`DISABLED_FEATURES` to `false`. From `backend`, migrate to head, then run
`python scripts/direct_client_conflict_e2e.py seed --manifest "$SELLORA_DIRECT_CONFLICT_MANIFEST"`.
From `frontend`, run `npm ci`, `npx playwright install --with-deps chromium`, then
`npm run test:e2e:direct-identity`. Remove the private manifest when finished and discard
the disposable database. Reruns require a fresh database and manifest; there are no
automatic retries against already mutated cases.

`--list`, TypeScript, lint, fixture guard tests and the prior component test validate
the harness structure only. They must not be reported as a browser/PostgreSQL pass
when Chromium or a disposable PostgreSQL server is unavailable. Visual quality and
production provider behavior are outside this bounded coverage.
