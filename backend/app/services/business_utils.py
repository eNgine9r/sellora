from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from app.database.base import model_to_dict


def json_safe(value: Any) -> Any:
    if isinstance(value, UUID | datetime | date | Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def snapshot(model: Any) -> dict[str, Any]:
    return json_safe(model_to_dict(model))
