# Sprint 1.5 CRM Completion

Sprint 1.5 completes core CRM customer enrichment without adding shipment implementation.

## Domain entities

- `Tag`: colored workspace tag.
- `CustomerTag`: customer/tag assignment, allowing many tags per customer.
- `CustomerNote`: append-only customer timeline note.
- `CustomerAddress`: customer address with one default address rule.
- `Attachment`: polymorphic attachment for Customer, Lead, Order, Product, and future Shipment records.

## Business rules

- Customers can have multiple tags.
- A customer may have only one default address; setting a new default clears previous defaults.
- Customer notes are append-only and expose no update/delete service or API routes.
- Attachments support `CUSTOMER`, `LEAD`, `ORDER`, `PRODUCT`, and `SHIPMENT` entity types.
