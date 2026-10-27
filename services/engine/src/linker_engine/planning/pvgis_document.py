"""Shared strict primitives for the two frozen JRC response formats."""

from __future__ import annotations

import json
import math
from typing import cast

from .canonical import Json, Object, encode
from .errors import InvalidInput


def unique_object(pairs: list[tuple[str, Json]]) -> Object:
    result: Object = {}
    for key, value in pairs:
        if key in result:
            raise InvalidInput("duplicate provider JSON field")
        result[key] = value
    return result


def number(row: Object, name: str) -> float:
    value = row.get(name)
    if type(value) not in (int, float):
        raise InvalidInput(f"finite numeric PVGIS {name} required")
    try:
        result = float(cast(float, value))
    except OverflowError as error:
        raise InvalidInput(f"representable numeric PVGIS {name} required") from error
    if not math.isfinite(result):
        raise InvalidInput(f"finite numeric PVGIS {name} required")
    return result


def read_object(content: bytes) -> Object:
    try:
        document = json.loads(content, object_pairs_hook=unique_object)
        if not isinstance(document, dict):
            raise InvalidInput("PVGIS response must be an object")
        encode(document)  # Validate even unused fields, not just model columns.
        return cast(Object, document)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise InvalidInput("PVGIS response is not finite JSON") from error
