"""Conservative UI-only projection of stored provider text (never changes an order).

Verified TrackingDocument codes take precedence when available. The heuristics
below only support pre-migration rows and must not treat unknown statuses as shipped.
"""
from app.models.shipment import ShipmentStatus


def infer_external_shipment_status(text: str | None) -> ShipmentStatus | None:
    clean = " ".join((text or "").casefold().split())
    if not clean:
        return None
    if any(word in clean for word in ("відмова", "повернен", "відмовив", "скасован")):
        return None
    if any(word in clean for word in ("отримано", "вручено", "доставлено", "одержано")):
        return ShipmentStatus.DELIVERED
    if any(word in clean for word in ("прибув", "прибула", "прибуло")):
        return ShipmentStatus.ARRIVED
    if ("прямує" in clean or "у дорозі" in clean or "в дорозі" in clean
            or ("відправлення у м." in clean and "очікуйте повідомлення" in clean)):
        return ShipmentStatus.IN_TRANSIT
    if any(word in clean for word in ("ще не надав до відправки", "створено", "зареєстровано")):
        return ShipmentStatus.CREATED
    return None
