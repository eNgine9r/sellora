"""Deterministic cargo description labels for an accessories catalogue.

Only recognized categories map to an explicit accessory type. Free-form product
names may classify a mixed/unknown category but are NEVER copied to the provider,
so SKUs, personal data, or internal markers cannot leak into TTN descriptions.
"""
from collections.abc import Iterable


_WATCH_CATEGORY = {"годинник", "годинники", "watch", "watches", "smartwatch", "розумні годинники"}
_JEWELRY_CATEGORY_WORDS = (
    "біжут", "прикрас", "браслет", "сереж", "каблуч", "кільц", "кольє",
    "ланцюж", "підвіск", "кулон", "хрестик", "намист", "перст",
)
_WATCH_NAME_HINTS = ("годинник", "годинники", "watch", "smartwatch")
_JEWELRY_NAME_HINTS = _JEWELRY_CATEGORY_WORDS


def accessory_cargo_description(lines: Iterable[tuple[str, str | None]]) -> str | None:
    """Return None when category cannot be established (caller uses safe fallback)."""
    groups: set[str] = set()
    unclassified = False
    seen = False
    for product_name, product_category in lines:
        seen = True
        category = (product_category or "").strip().casefold()
        name = product_name or ""
        if category in _WATCH_CATEGORY or "годинник" in category:
            groups.add("годинник")
        elif any(term in category for term in _JEWELRY_CATEGORY_WORDS):
            groups.add("біжутерія")
        else:
            name_watch = any(word in name.casefold() for word in _WATCH_NAME_HINTS)
            name_jewelry = any(word in name.casefold() for word in _JEWELRY_NAME_HINTS)
            if name_watch:
                groups.add("годинник")
            if name_jewelry:
                groups.add("біжутерія")
            if not name_watch and not name_jewelry:
                unclassified = True

    if not seen:
        return None
    if unclassified:
        # Never silently describe an unknown accessory as jewelry or watches.
        return "Аксесуари" if groups else None
    if groups == {"годинник"}:
        return "Аксесуари (годинник)"
    if groups == {"біжутерія"}:
        return "Аксесуари (біжутерія)"
    if groups == {"годинник", "біжутерія"}:
        return "Аксесуари (годинник, біжутерія)"
    return None
