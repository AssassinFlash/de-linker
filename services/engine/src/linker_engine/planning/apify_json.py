"""Strict finite JSON; ambiguous duplicate names never choose provider authority."""

from __future__ import annotations

import json
from typing import cast

from .canonical import Json, Object, encode
from .errors import InvalidInput
from .weather_fetch_errors import WeatherResponseInvalid


def _unique(pairs: list[tuple[str, Json]]) -> Object:
    result: Object = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("duplicate JSON member")
        result[name] = value
    return result


def apify_json(content: bytes) -> Json:
    try:
        value = json.loads(content.decode("utf-8"), object_pairs_hook=_unique)
        encode(value)
        return cast(Json, value)
    except (ValueError, UnicodeError, InvalidInput, RecursionError):
        raise WeatherResponseInvalid("invalid or ambiguous provider JSON") from None
