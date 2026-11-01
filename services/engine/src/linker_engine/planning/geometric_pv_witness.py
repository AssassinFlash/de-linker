"""Bounded projection of an existing canonical geometric-PV witness.

The original CAS bytes and hashes do not change. Module rows are validated
individually, so readers can discard the large diagnostic arrays they do not
use instead of materializing the entire annual document.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from .canonical import Json, Object, decode_object
from .errors import VersionUnavailable
from .storage import Blobs

_TOKEN = re.compile(rb'"(?:[^"\\]|\\.)*"|[\[\]{}]')


def project_witness(
    blobs: Blobs,
    sha256: str,
    *,
    module_fields: tuple[str, ...] = (),
    checkpoint: Callable[[], None] = lambda: None,
) -> Object:
    """Verify the whole original blob and retain only requested module fields."""
    with blobs.mapped(sha256) as data:
        stack: list[bytes] = []
        start: int | None = None
        end: int | None = None
        row_start: int | None = None
        previous: int | None = None
        rows: list[Json] = []
        for match in _TOKEN.finditer(data):
            token = match.group()
            if token.startswith(b'"'):
                if (
                    len(stack) == 1
                    and token == b'"modules"'
                    and data[match.end() : match.end() + 1] == b":"
                ):
                    if (
                        start is not None
                        or data[match.end() + 1 : match.end() + 2] != b"["
                    ):
                        raise VersionUnavailable("invalid geometric PV module array")
                    start = match.end() + 1
                continue
            if token in (b"{", b"["):
                if start is not None and end is None and len(stack) == 2:
                    if token != b"{" or row_start is not None:
                        raise VersionUnavailable("invalid geometric PV module row")
                    separator = data[
                        (
                            previous if previous is not None else start + 1
                        ) : match.start()
                    ]
                    if separator != (b"," if previous is not None else b""):
                        raise VersionUnavailable(
                            "invalid geometric PV module separator"
                        )
                    row_start = match.start()
                stack.append(token)
                continue
            if (
                not stack
                or (token == b"}" and stack[-1] != b"{")
                or (token == b"]" and stack[-1] != b"[")
            ):
                raise VersionUnavailable("invalid geometric PV witness structure")
            if row_start is not None and len(stack) == 3 and token == b"}":
                checkpoint()
                row = decode_object(data[row_start : match.end()])
                if module_fields:
                    if any(key not in row for key in module_fields):
                        raise VersionUnavailable("incomplete frozen series witness")
                    rows.append({key: row[key] for key in module_fields})
                previous, row_start = match.end(), None
            if start is not None and end is None and len(stack) == 2 and token == b"]":
                if (
                    row_start is not None
                    or data[
                        (
                            previous if previous is not None else start + 1
                        ) : match.start()
                    ]
                    != b""
                ):
                    raise VersionUnavailable("invalid geometric PV module array")
                end = match.end()
            stack.pop()
        if start is None or end is None or stack:
            raise VersionUnavailable("incomplete geometric PV witness")
        summary = decode_object(data[:start] + b"[]" + data[end:])
        summary["modules"] = rows
        return summary
