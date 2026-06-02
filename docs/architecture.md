# Sellora Architecture

Sellora is bootstrapped as a Clean Architecture modular monolith. The backend keeps framework, persistence, API, authentication, and domain-facing service code in explicit packages so future CRM modules can be added without creating early distributed-system complexity.

## Backend layers

- `app/models`: SQLAlchemy persistence models for identity, workspaces, roles, memberships, and audit logs.
- `app/schemas`: Pydantic v2 request/response DTOs.
- `app/repositories`: database access abstractions.
- `app/services`: application use cases and orchestration.
- `app/api`: FastAPI routers and transport concerns.
- `app/dependencies`: authentication, RBAC, and tenant access guards.
- `app/database`: SQLAlchemy base metadata, sessions, and reusable database mixins including `WorkspaceScopedMixin` and `SoftDeleteMixin`.

## Multi-tenant foundation

Every future business entity must inherit `WorkspaceScopedMixin` for the indexed `workspace_id` foreign key and `SoftDeleteMixin` for consistent soft deletion. API routes should require `X-Workspace-ID`, call tenant/RBAC dependencies, and repository queries should constrain by `workspace_id` and active records (`deleted_at IS NULL`) before returning tenant-owned data.

## Sprint 1.1 scope boundaries

This sprint intentionally does not implement Leads, Orders, Customers, Products, Inventory, Advertising, Finance, or Shipments. Those modules should be introduced in later sprints as isolated feature packages that depend on the shared identity, RBAC, audit, and tenant foundations.

## Future entity mixin contract

Future CRM models should use `UUIDPrimaryKeyMixin`, `WorkspaceScopedMixin`, `SoftDeleteMixin`, and `TimestampMixin` together. This keeps tenant isolation, soft deletion, audit-friendly actor tracking, and timestamps consistent across modules without implementing business domains in Sprint 1.1.

## Sprint 1.2A business modules

Lead Sources, Leads, and Customers are the first business modules. They inherit the database mixin contract, keep business rules in services, expose repositories for persistence, and write audit logs for create/update/delete and workflow transitions. Orders, Products, Inventory, and Advertising remain out of scope.
