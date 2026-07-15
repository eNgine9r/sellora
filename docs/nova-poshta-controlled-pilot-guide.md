# Nova Poshta controlled pilot guide — Sprint 8E

1. Use a dedicated synthetic QA8E workspace and synthetic order only.
2. Configure the Nova Poshta key through Settings → Integrations; do not commit the key or expose it in screenshots.
3. Validate the key and sender configuration.
4. Search city and warehouse through read-only provider calls.
5. Create one eligible local shipment draft for a synthetic order.
6. Enable provider writes only in the guarded staging workflow with `STAGING_NOVA_POSHTA_ALLOW_WRITES=true`.
7. Create exactly one controlled TTN and verify duplicate-click protection.
8. Refresh status manually and verify normalized status mapping.
9. If cancellation/delete is required, Sprint 8E records it as deferred because the current repository has no provider cancellation operation.
10. Clean up Sellora synthetic records and provider-side document manually if needed; preserve only sanitized evidence.
