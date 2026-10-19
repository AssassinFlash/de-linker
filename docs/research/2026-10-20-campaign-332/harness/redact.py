"""Strip token-shaped strings before evidence is written."""

from __future__ import annotations

import re
from typing import Any

# The service token is 32 random bytes as hex (tools/local services.py).
# Chunk ids and turn ids are shorter or punctuated, so they stay.
_SECRET = re.compile(
    r"Bearer\s+\S+|\bsk-[A-Za-z0-9_-]{8,}|\b[0-9a-fA-F]{64}\b",
)


def redact_text(value: str) -> str:
    return _SECRET.sub("[redacted]", value)


def redact(value: Any) -> Any:
    """Walk JSON-shaped data and redact secret-shaped strings."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in {"authorization", "x-linker-service-token", "token"}:
                cleaned[key] = "[redacted]"
            else:
                cleaned[key] = redact(item)
        return cleaned
    return value
