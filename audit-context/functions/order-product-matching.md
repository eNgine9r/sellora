## `ProductMatchingService.match` in backend/app/ai/services/product_matching_service.py (L18-L25)

**Purpose:** Existing unused foundation for mapping free text to a product. It currently returns product ID only, not orderable variant.

**Inputs & Assumptions:**
- Workspace UUID, text, threshold default0.85.
- Repository product search uses workspace/deleted filters and ILIKE product.name OR product.sku (product_repository.py L18-L25).
- Product search ordering is newest created first; first candidate is assumed best. Evidence of semantic ranking, tie comparison or variant disambiguation: **nothing found**.
- Threshold is a rule score cutoff, not a calibrated probability.

**Outputs & Effects:**
- No writes or external calls.
- NOT_FOUND if no active product. Else first active candidate gets0.9 for name substring or0.65 otherwise; status MATCHED/AMBIGUOUS by threshold; alternatives always empty; matched_variant_id remains None (L19-L25).
- Source search found no runtime caller; only ProductMatchResult imported in test_ai_foundation.py L7/L29-L32. ProductMatchingService is a foundation, not active end-to-end product recognition.

**Block-by-Block:**

```python
# L19-L22
normalized = text.casefold().strip()
candidates = self.products.list_for_workspace(workspace_id, search=normalized[:80])[:20]
active = [p for p in candidates if p.is_active]
if not active: return ProductMatchResult(status='NOT_FOUND')
```
- **What:** Product title/SKU substring lookup then active filtering.
- **Why here:** No result is returned for inactive-only products.
- **Assumes:** Up to20 newest substring matches sufficiently cover intended catalog entity.
- **Establishes:** Returned product is from the queried workspace and nondeleted.
- **Depended on by:** Candidate choice.

```python
# L23-L25
best = active[0]
confidence = 0.9 if normalized and normalized in best.name.casefold() else 0.65
return ProductMatchResult(...matched_product_id=best.id,...)
```
- **What:** Returns first candidate using a fixed heuristic score.
- **Why here:** No additional validation stage exists.
- **Assumes:** First is unique/best; **nothing found** establishing uniqueness.
- **Establishes:** No variant is chosen; cannot directly become OrderItemCreate, which requires product_variant_id (schemas/order.py L10-L14).
- **Depended on by:** Currently no callers.

**Cross-Function Dependencies:**
- ProductRepository list/search detailed above; includes images, no pagination.
- ProductVariantRepository exists in constructor but is unused in match (L16-L17).
- Available variant repository operations: workspace+product list (product_repository.py L52-L56), workspace get (L58-L60), product/color/size identity (L62-L64, no workspace parameter; only use after product scope validated), workspace exact case-sensitive SKU lookup (L66-L70).
- Existing /products search and /products/variants?product_id endpoints require ANALYST membership, service delegates to repositories (api/v1/products.py L20-L32; product_service.py L31-L35,L112-L116).
- Variant rows have SKU,color,size,nullable price,active flag; no catalog cost (models/product_variant.py L12-L25).
- Fulfillment backend still revalidates variant workspace/deletion/active and inventory under lock when creating real order (order_service.py L69-L82,L298-L304).

**Open Questions:**
- Exact SKU, repeated product names, color/size mismatch, variant active state and availability need explicit contracts before using this service to propose order lines.
- Schema AIWorkspaceSettings.minimum_product_match_confidence exists (models/ai_direct.py L293; response schema L169), but this matcher is not currently wired to it.
- No product-mention-specific confidence or source IDs are in existing structured output; inference confidence should not be relabeled as match confidence.
