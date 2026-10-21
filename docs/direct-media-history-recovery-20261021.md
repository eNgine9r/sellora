# Sellora Direct Media & History Recovery (2026-10-21)

## Scope

- Parse Meta `message.attachments` (image, `ig_post`, audio, video, etc.) without losing messages containing text and attachments.
- Preserve Meta source URLs in **internal workspace-scoped JSONB only**. They must never appear in Direct API JSON, error messages, logs or frontend URLs.
- Serve supported formats through an authenticated **OWNER/MANAGER** private endpoint, with workspace/conversation enforcement, trusted Meta CDN host allowlist, HTTPS-only, no cross-host untrusted redirects, MIME allowlist, size cap, filesystem private permissions and `no-store` responses.
- Prefer durable local private cache on `/app/storage/direct-media`, using the existing persistent backend volume on Raspberry Pi. Never use `/public`, `/static` or shared CDN.
- Optional background cache `DIRECT_MEDIA_CACHE_ENABLED=true` (default false), processing 5 messages per 30 seconds. The GET endpoint also caches media on first authorized access.
- Backfill metadata for previously processed webhook messages without duplicating Direct messages or changing orders, customers, payment state or workspace membership.
- Read paginated **message** pages with a total cap of 200 per conversation/request, while keeping provider rate-limit retry and no-duplicate checks. Older messages may be unavailable under Meta API restrictions.

## Read-only recovery preview

From backend container with the current release code and database configured:

```sh
python scripts/backfill_direct_media.py --workspace-id YOUR_EXISTING_WORKSPACE_UUID
```

Review summary counts and the DB backup. Only then:

```sh
python scripts/backfill_direct_media.py --workspace-id YOUR_EXISTING_WORKSPACE_UUID --apply
```

The script prints counts only; no signed media URLs, Instagram message contents or provider IDs. It modifies only `direct_messages.attachment_metadata` and, when formerly `UNSUPPORTED`, `message_payload_type`. It does **not** download bank screenshots.

## Security / rollout gates

1. Confirm a valid encrypted and restorable database backup and a persistent private media volume before enabling automatic caching.
2. Confirm backend test suite, TypeScript check and staging smoke checks; confirm both workspace roles and existing login remain correct.
3. Rollout backend and frontend together; confirm media opens when authorized but fails for unauthenticated/foreign workspace and unsupported URL.
4. Run recovery preview; apply only if its per-workspace count is expected. No broad re-import on the real Your Jewelry workspace.
5. Confirm no automated change to `PAID` based on a screenshot. A bank screenshot is evidence, not payment verification.
6. Confirm retention/erasure backup policy for private attachments before public multi-tenant release.

## Remaining product scope

- Direct-to-order linking of payment proofs is deliberately not automated in this patch. Requires explicit manager action, audit log and retention design.
- Meta may not provide all old message details even if message IDs can be paged. The UI indicates **checked available history**, not guaranteed complete Instagram history.
- A per-conversation manual history retry with durable cursor tracking, as distinct from bounded workspace-wide history import, belongs to follow-up hardening.
