# Sprint 1.2A Lead to Customer Workflow

Sprint 1.2A introduces the first Sellora business workflow: lead capture, qualification support, assignment, loss tracking, and conversion to a customer.

## Domain entities

- `LeadSource`: workspace-scoped and soft-deletable source catalog such as Instagram Direct, Instagram Ads, Telegram, Facebook, Repeat Customer, and Manual.
- `Lead`: workspace-scoped and soft-deletable prospect with status values `NEW`, `IN_PROGRESS`, `QUALIFIED`, `CONVERTED`, and `LOST`.
- `Customer`: workspace-scoped and soft-deletable customer created manually or through lead conversion.

## Business rules

- Lead creation defaults to `NEW` and writes an audit log.
- Lead assignment changes `assigned_user_id` and writes an audit log.
- Lead conversion creates a customer, copies name/phone/Instagram username, marks the lead `CONVERTED`, keeps the original lead, and writes audit logs.
- Marking a lead `LOST` requires a `loss_reason` and writes an audit log.
- All API routes require workspace context through `X-Workspace-ID`.

## RBAC

- `OWNER` and `MANAGER`: full create/read/update/delete and workflow actions.
- `ANALYST`: read-only access to lead sources, leads, and customers.
