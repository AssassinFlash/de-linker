"""The permanent-source contract shared by imports and durable publication."""

from __future__ import annotations

from .canonical import Object
from .errors import InvalidInput


def validate_asset(
    content: bytes, media_type: str, purpose: str, metadata: Object
) -> None:
    if not content or not media_type.strip() or not purpose.strip():
        raise InvalidInput("nonempty asset, media type and purpose required")
    if metadata.get("retention") != "permanent":
        raise InvalidInput("this source needs a compliant temporary asset store")
    provenance = metadata.get("provenance")
    if not isinstance(provenance, dict) or any(
        not isinstance(provenance.get(name), str) or not str(provenance[name]).strip()
        for name in ("label", "basis", "rights_basis")
    ):
        raise InvalidInput("source label, fact basis and retention rights required")
