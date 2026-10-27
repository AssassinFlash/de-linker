"""The bounded source, rather than csv's implicit field ceiling, bounds cells."""

from __future__ import annotations

import csv
import io
from threading import Lock
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _csv import Reader

_field_limit_lock = Lock()


def source_reader(text: str, delimiter: str) -> Reader:
    # csv.field_size_limit is process-wide. Only raise it, under one lock;
    # resetting it could break a larger concurrent reader. HTTP intake bounds
    # the source bytes before decoding. No field can exceed its source text.
    with _field_limit_lock:
        if csv.field_size_limit() < len(text):
            csv.field_size_limit(len(text))
    return csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
