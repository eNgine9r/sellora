# Sprint 8C staging closure blocker

## Status

Sprint 8C final staging closure is blocked at Gate 2.

## Finding

The durable dry-run approval signature is stored in PostgreSQL, but the uploaded import source is stored only at `IMPORT_STORAGE_PATH` and referenced by `ImportJob.file_path`.

The default path is `storage/imports`. On the current Render deployment this is local ephemeral filesystem storage unless a Persistent Disk is mounted at the configured path.

After a Render restart or redeploy:

- the PostgreSQL `IMPORT_DRY_RUN_APPROVED` audit record can remain available;
- the local source file can be lost;
- `ImportExecutionGuard` rejects execute with `Import source file is unavailable; upload and dry-run again`;
- therefore durable approval across a real restart boundary is not proven.

## Required narrow fix

For controlled pilot closure, configure durable source-file storage before rerunning Gate 2.

Fastest controlled-pilot option:

1. Attach a Render Persistent Disk at `/app/storage`.
2. Set `IMPORT_STORAGE_PATH=/app/storage/imports`.
3. Redeploy the backend.
4. Run upload → dry-run → backend restart/redeploy → execute with the same job/input.

Long-term scale option:

Use private object storage (for example Supabase Storage/S3-compatible storage) and keep only a workspace-scoped object key, immutable hash, size, and retention metadata in PostgreSQL.

## Scope control

This is a Sprint 8C closure/infrastructure defect. It is not Sprint 8D and does not add a new Import Center feature.

## Release decision

- Core controlled pilot without Import Center: GREEN.
- Import Center pilot: HOLD.
- Sprint 8C final approval: BLOCKED until Gate 2 passes.
