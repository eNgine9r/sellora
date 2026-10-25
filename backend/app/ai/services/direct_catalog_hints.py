"""Conservative suggestions for a conversation from active *scoped* catalog.

A generic category mention is NEVER an exact product choice. All inferred
suggestions require the manager to inspect source evidence and select a
variant explicitly. No extra provider calls or stock mutations.
"""
import re
from dataclasses import dataclass

from app.ai.services.product_matching_service import normalize_product_text


@dataclass(frozen=True)
class CatalogHint:
    phrase: str
    matched_by: str
    rows: list  # [(ProductVariant, Product)]
    ambiguous: bool
    identity: str


# Recognize only grounded product-family nouns, not generic words such as
# "це", "є", "ціна", or a bare social-network URL.
_FAMILY_RULES: tuple[tuple[re.Pattern, tuple[str, ...]], ...] = (
    (re.compile(r"(?<!\w)браслет\w*(?!\w)"), ("браслет",)),
    (re.compile(r"(?<!\w)сереж\w*(?!\w)"), ("сереж",)),
    (re.compile(r"(?<!\w)(?:каблуч\w*|кільц\w*)(?!\w)"), ("каблуч", "кільц")),
    (re.compile(r"(?<!\w)(?:годинник\w*|годиннич\w*|watch|watches)(?!\w)"), ("годинник", "watch")),
    (re.compile(r"(?<!\w)(?:підвіск\w*|кулон\w*)(?!\w)"), ("підвіск", "кулон")),
    (re.compile(r"(?<!\w)ланцюж\w*(?!\w)"), ("ланцюж",)),
    (re.compile(r"(?<!\w)кольє(?!\w)"), ("кольє",)),
    (re.compile(r"(?<!\w)намист\w*(?!\w)"), ("намист",)),
)


def suggest_from_catalog(text: str, catalog: list) -> list[CatalogHint]:
    normalized = normalize_product_text(text)
    if not normalized or not catalog:
        return []
    hints: list[CatalogHint] = []

    # Full multiword product titles provide stronger evidence than categories,
    # but a title with multiple variants is still ambiguous.
    titles: dict[str, list] = {}
    for variant, product in catalog:
        title = normalize_product_text(product.name)
        if len(title) >= 9 and len(title.split()) >= 2 and len(title) <= 200:
            titles.setdefault(title, []).append((variant, product))

    exact_titles = []
    for title, rows in titles.items():
        match = re.search(r"(?<!\w)" + re.escape(title) + r"(?!\w)", normalized)
        if match:
            exact_titles.append((title, rows))
    # Prefer the longest grounded title in this message, no broad category
    # fallback when a precise title has already been found.
    if exact_titles:
        for title, rows in sorted(exact_titles, key=lambda hit: -len(hit[0]))[:4]:
            hints.append(CatalogHint(title, "EXACT_PRODUCT_TITLE", rows, len(rows) != 1, title))
        return hints

    for family_index, (pattern, category_terms) in enumerate(_FAMILY_RULES):
        match = pattern.search(normalized)
        if not match:
            continue
        rows = [
            (variant, product) for variant, product in catalog
            if any(token in normalize_product_text(product.category) for token in category_terms)
        ]
        if not rows:
            continue
        # Group every plausible variant. Never select a random item just
        # because the display list will be capped at ten.
        hints.append(CatalogHint(match.group(0), "PRODUCT_CATEGORY", rows, len(rows) != 1, f"family-{family_index}"))
        if len(hints) >= 4:
            break
    return hints
