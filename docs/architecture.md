# Sellora Architecture

Sellora is bootstrapped as a Clean Architecture modular monolith. The backend keeps framework, persistence, API, authentication, and domain-facing service code in explicit packages so future CRM modules can be added without creating early distributed-system complexity.

## Backend layers

- `app/models`: SQLAlchemy persistence models for identity, workspaces, roles, memberships, and audit logs.
- `app/schemas`: Pydantic v2 request/response DTOs.
- `app/repositories`: database access abstractions.
- `app/services`: application use cases and orchestration.
- `app/api`: FastAPI routers and transport concerns.
- `app/dependencies`: authentication, RBAC, and tenant access guards.
- `app/database`: SQLAlchemy base metadata, sessions, and tenant-aware mixins.

## Multi-tenant foundation

Every future business entity should include `workspace_id` and use the shared `TenantMixin`. API routes should require `X-Workspace-ID` and call tenant/RBAC dependencies before querying tenant-owned data.

## Sprint 1.1 scope boundaries

This sprint intentionally does not implement Leads, Orders, Customers, Products, Inventory, Advertising, Finance, or Shipments. Those modules should be introduced in later sprints as isolated feature packages that depend on the shared identity, RBAC, audit, and tenant foundations.
