"""The planning JSON encoding: sorted UTF-8 keys, finite values, no implicit conversions."""

from __future__ import annotations

import hashlib
import json
import math
from typing import cast

from .errors import InvalidInput, VersionUnavailable

type Json = None | bool | int | float | str | list[Json] | dict[str, Json]
type Object = dict[str, Json]


def _validate(value: object) -> None:
    if value is None or type(value) in (bool, int):
        return
    if type(value) is str:
        try:
            value.encode("utf-8")
        except UnicodeError as error:
            raise InvalidInput("JSON strings must be valid Unicode") from error
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise InvalidInput("non-finite number")
        return
    if type(value) is list:
        for item in value:
            _validate(item)
        return
    if type(value) is dict:
        for key, item in value.items():
            if not isinstance(key, str):
                raise InvalidInput("JSON object keys must be strings")
            _validate(key)
            _validate(item)
        return
    raise InvalidInput("value is not JSON")


def encode(value: Json) -> bytes:
    """Hash exactly the validated representation used for storage and replay."""
    _validate(value)
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def decode_object(content: bytes) -> Object:
    try:
        value = json.loads(content)
        _validate(value)
    except (ValueError, UnicodeError, InvalidInput) as error:
        raise VersionUnavailable("invalid pinned JSON") from error
    if not isinstance(value, dict):
        raise VersionUnavailable("pinned document must be an object")
    return cast(Object, value)
