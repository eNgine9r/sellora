from dataclasses import dataclass, field
import unicodedata
from uuid import UUID

from app.ai.schemas.structured_output import ProductMention
from app.repositories.product_repository import ProductRepository, ProductVariantRepository


def normalize_product_text(value: str | None) -> str:
    return " ".join(unicodedata.normalize("NFKC", value or "").casefold().split())


@dataclass
class ProductMatchResult:
    status: str
    matched_product_id: UUID | None = None
    matched_variant_id: UUID | None = None
    confidence: float = 0  # Legacy compatibility; never a matching probability.
    matched_by: list[str] = field(default_factory=list)
    alternatives: list[dict] = field(default_factory=list)
    clarification_required: bool = True


@dataclass
class CatalogMatch:
    status: str
    reason: str
    matched_by: str | None = None
    rows: list = field(default_factory=list)


class ProductMatchingService:
    def __init__(self, products: ProductRepository, variants: ProductVariantRepository) -> None:
        self.products = products
        self.variants = variants

    def match_mention(self, mention: ProductMention, catalog: list) -> CatalogMatch:
        sku = normalize_product_text(mention.sku)
        text = normalize_product_text(mention.text)
        if sku:
            rows = [(variant, product) for variant, product in catalog if normalize_product_text(variant.sku) == sku]
            matched_by = "VARIANT_SKU"
            if not rows:
                rows = [(variant, product) for variant, product in catalog if normalize_product_text(product.sku) == sku]
                matched_by = "PRODUCT_SKU"
            if not rows:
                return CatalogMatch("NOT_FOUND", "UNKNOWN_SKU")
        else:
            rows = [(variant, product) for variant, product in catalog if text and text in {
                normalize_product_text(product.name), normalize_product_text(product.sku), normalize_product_text(variant.sku),
            }]
            matched_by = "EXACT_TITLE_OR_SKU"
        narrowed = [(variant, product) for variant, product in rows if all(
            not normalize_product_text(expected) or normalize_product_text(actual) == normalize_product_text(expected)
            for expected, actual in [(mention.color, variant.color), (mention.size, variant.size)]
        )]
        if rows and not narrowed:
            return CatalogMatch("NOT_FOUND", "SKU_ATTRIBUTE_CONFLICT" if sku else "ATTRIBUTE_CONFLICT")
        if not narrowed:
            return CatalogMatch("NOT_FOUND", "NO_EXACT_MATCH")
        if len(narrowed) > 1:
            return CatalogMatch("AMBIGUOUS", "MULTIPLE_VARIANTS", matched_by, narrowed)
        return CatalogMatch("MATCHED", "UNIQUE_EXACT_MATCH", matched_by, narrowed)

    def match(self, workspace_id: UUID, text: str, threshold: float = 0.85) -> ProductMatchResult:
        # Preserve the unused foundation's entrypoint without its first-row guess.
        catalog = self.variants.proposal_catalog(workspace_id)
        if len(catalog) > 500:
            return ProductMatchResult(status="NOT_FOUND")
        result = self.match_mention(ProductMention(text=text[:240]), catalog)
        unique = result.rows[0] if result.status == "MATCHED" else None
        return ProductMatchResult(
            status=result.status, matched_product_id=unique[1].id if unique else None,
            matched_variant_id=unique[0].id if unique else None,
            matched_by=[result.matched_by] if result.matched_by else [],
            alternatives=[{"product_id": product.id, "variant_id": variant.id} for variant, product in result.rows[:10]],
            clarification_required=result.status != "MATCHED",
        )
