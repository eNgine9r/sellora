"""Conservative mapping of Nova Poshta TrackingDocument status codes.

Refusals, returns-in-progress, financial remittances and unknown codes are
NOT equivalent to a completed return or a confirmed payment.
"""
from app.models.shipment import ShipmentStatus

CODE_STATES: dict[str, ShipmentStatus] = {
    "1": ShipmentStatus.CREATED,
    "4": ShipmentStatus.IN_TRANSIT,
    "41": ShipmentStatus.IN_TRANSIT,
    "5": ShipmentStatus.IN_TRANSIT,
    "6": ShipmentStatus.IN_TRANSIT,
    "7": ShipmentStatus.ARRIVED,
    "8": ShipmentStatus.ARRIVED,
    "9": ShipmentStatus.DELIVERED,
    "10": ShipmentStatus.DELIVERED,
    "11": ShipmentStatus.DELIVERED,
    "12": ShipmentStatus.ARRIVED,
    "101": ShipmentStatus.IN_TRANSIT,
}

# Treat terminal delivery as final, and don't regress when provider data lags.
_PROGRESS = {
    ShipmentStatus.DRAFT: 0,
    ShipmentStatus.CREATED: 1,
    ShipmentStatus.IN_TRANSIT: 2,
    ShipmentStatus.ARRIVED: 3,
    ShipmentStatus.DELIVERED: 4,
}


def normalize_tracking_status(code: str | None, text: str | None = None) -> ShipmentStatus | None:
    if code is not None and str(code).strip():
        return CODE_STATES.get(str(code).strip())
    # Compatibility with older/test clients that only return Status strings.
    clean = (text or "").casefold().strip()
    if clean in ("delivered", "отримано", "доставлено", "вручено"):
        return ShipmentStatus.DELIVERED
    if clean in ("arrived", "прибуло у відділення", "прибуло до відділення"):
        return ShipmentStatus.ARRIVED
    if clean in ("in transit", "у дорозі", "відправлено"):
        return ShipmentStatus.IN_TRANSIT
    if clean in ("created", "створено"):
        return ShipmentStatus.CREATED
    if clean in ("returned", "повернено відправнику"):
        return ShipmentStatus.RETURNED
    return None


def should_apply_tracking_status(previous: ShipmentStatus, incoming: ShipmentStatus | None) -> bool:
    if incoming is None or previous in (ShipmentStatus.RETURNED, ShipmentStatus.CANCELLED):
        return False
    if incoming == ShipmentStatus.RETURNED:
        return previous in (ShipmentStatus.IN_TRANSIT, ShipmentStatus.ARRIVED, ShipmentStatus.DELIVERED)
    if previous in _PROGRESS and incoming in _PROGRESS:
        return _PROGRESS[incoming] > _PROGRESS[previous]
    return False
