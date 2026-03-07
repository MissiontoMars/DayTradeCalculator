from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def uuid4_str() -> str:
    return str(uuid.uuid4())


def json_dumps(obj: Any) -> str:
    def default(o: Any) -> Any:
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, Decimal):
            return str(o)
        raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")

    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=default)


def json_loads(s: str | None) -> Any:
    if not s:
        return None
    return json.loads(s)
