from dataclasses import dataclass, field
from uuid import UUID
from app.repositories.product_repository import ProductRepository, ProductVariantRepository

@dataclass
class ProductMatchResult:
    status: str
    matched_product_id: UUID | None = None
    matched_variant_id: UUID | None = None
    confidence: float = 0
    matched_by: list[str] = field(default_factory=list)
    alternatives: list[dict] = field(default_factory=list)
    clarification_required: bool = True

class ProductMatchingService:
    def __init__(self, products: ProductRepository, variants: ProductVariantRepository) -> None:
        self.products = products; self.variants = variants
    def match(self, workspace_id: UUID, text: str, threshold: float = 0.85) -> ProductMatchResult:
        normalized = text.casefold().strip()
        candidates = self.products.list_for_workspace(workspace_id, search=normalized[:80])[:20]
        active = [p for p in candidates if p.is_active]
        if not active: return ProductMatchResult(status='NOT_FOUND')
        best = active[0]
        confidence = 0.9 if normalized and normalized in best.name.casefold() else 0.65
        return ProductMatchResult(status='MATCHED' if confidence >= threshold else 'AMBIGUOUS', matched_product_id=best.id, confidence=confidence, matched_by=['title'], alternatives=[], clarification_required=confidence < threshold)
