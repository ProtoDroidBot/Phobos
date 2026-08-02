"""Convert mixed Python 2/client values into deterministic JSON-safe data."""

from __future__ import annotations

import base64
import hashlib
import math
from collections.abc import Mapping
from decimal import Decimal


def bytes_envelope(value):
    raw = bytes(value)
    return {
        "$type": "bytes",
        "encoding": "base64",
        "length": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "data": base64.b64encode(raw).decode("ascii"),
    }


def _safe_key(value):
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return "bytes:" + base64.b64encode(value).decode("ascii")
    return str(value)


def to_json_safe(value):
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return {"$type": "float", "value": repr(value)}
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes_envelope(value)
    if isinstance(value, Mapping):
        return {_safe_key(key): to_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_json_safe(item) for item in value]
    if hasattr(value, "_asdict"):
        return to_json_safe(value._asdict())
    if hasattr(value, "__dict__"):
        return to_json_safe({key: item for key, item in vars(value).items() if not key.startswith("_")})
    return str(value)
