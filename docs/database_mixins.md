# Database Mixins

Sellora uses reusable SQLAlchemy mixins to keep future tenant-owned CRM entities consistent without introducing business modules during the bootstrap sprint.

## `WorkspaceScopedMixin`

`WorkspaceScopedMixin` adds a required `workspace_id` column with an index and a foreign key to `workspaces.id`. Future business entities must inherit this mixin so all repository queries can be constrained to the active workspace.

## `SoftDeleteMixin`

`SoftDeleteMixin` adds nullable `deleted_at` and `deleted_by` columns. Future business repositories should filter active records with `deleted_at IS NULL` and set `deleted_by` to the user performing the delete when available.

## Future model pattern

Future business entities should inherit the mixins in this shape:

```python
class FutureEntity(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "future_entities"
```

See `docs/future_model_examples.py` for an illustrative non-imported example. It is documentation only and does not implement Leads, Orders, Customers, Products, Inventory, Advertising, Finance, or Shipments.
