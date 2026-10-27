"""Interoperable JSON numbers for browser/PHP/Python commands.

The maximum is 2**53 - 1 (binary64's exact integer window), a representation
policy, not an engineering limit. Trusted internal CAS has a broader domain.
"""

from __future__ import annotations

import math

MAX_WIRE_NUMBER = 2**53 - 1


def check_wire_numbers(value: object) -> None:
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is int:
            if abs(item) > MAX_WIRE_NUMBER:
                raise ValueError("number outside the interoperable JSON range")
        elif type(item) is float:
            if not math.isfinite(item) or abs(item) > MAX_WIRE_NUMBER:
                raise ValueError("number outside the interoperable JSON range")
        elif isinstance(item, dict):
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
