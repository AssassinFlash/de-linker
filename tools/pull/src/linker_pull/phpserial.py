"""Changing the strings inside PHP-serialized data without breaking it.

WordPress stores arrays and objects with PHP's serialize() (maybe_serialize()),
which prefixes every string with its length in bytes: s:5:"hello";. Replacing
text inside such a value changes that length, so the value is walked token by
token and every string is written back with its new length, as WP-CLI's
search-replace does by unserializing and serializing again.

Grammar (php-src ext/standard/var.c, php_var_serialize_intern): N; b:0; i:-3;
d:0.5; s:<bytes>:"…"; a:<n>:{key value …} O:<len>:"Class":<n>:{name value …}
C:<len>:"Class":<len>:{…} E:<len>:"Enum:Case"; r:<n>; R:<n>;. C: and E: are
copied as they are.
"""

from __future__ import annotations

import re
from collections.abc import Callable

# change(text, key) -> new text; `key` is the array key or property name the
# string is stored under, None at the top level and for keys themselves.
Change = Callable[[str, str | None], str]

SCALAR = re.compile(rb"(?:b:[01]|i:-?\d+|d:[^;]+);")
REFERENCE = re.compile(rb"[rR]:\d+;")
STRING_HEAD = re.compile(rb's:(\d+):"')
ARRAY_HEAD = re.compile(rb"a:(\d+):\{")
OBJECT_HEAD = re.compile(rb'O:(\d+):"')
CUSTOM_HEAD = re.compile(rb'C:(\d+):"')
ENUM_HEAD = re.compile(rb'E:(\d+):"')
# Strings serialize() can produce at the top level and that can hold strings.
CANDIDATE = re.compile(r"(?:[aO]:\d+:|s:\d+:\")")


class NotSerialized(ValueError):
    """The bytes are not one serialized PHP value."""


def looks_serialized(text: str) -> bool:
    """Cheap test before a parse: an array, an object or a string at the top level."""
    return CANDIDATE.match(text) is not None and text[-1:] in ("}", ";")


def rewrite(text: str, change: Change) -> str | None:
    """`text` with `change` applied to every string in it; None unless it is serialized."""
    data = encode(text)
    try:
        end, out = _value(data, 0, change, None)
    except (NotSerialized, IndexError, ValueError):
        return None
    if end != len(data):
        return None
    return decode(out)


def encode(text: str) -> bytes:
    return text.encode("utf-8", "surrogateescape")


def decode(data: bytes) -> str:
    return data.decode("utf-8", "surrogateescape")


def _value(data: bytes, at: int, change: Change, key: str | None) -> tuple[int, bytes]:
    if data.startswith(b"N;", at):
        return at + 2, b"N;"
    found = SCALAR.match(data, at) or REFERENCE.match(data, at)
    if found:
        return found.end(), found.group()
    head = STRING_HEAD.match(data, at)
    if head:
        end, payload = _quoted(data, head, b'";')
        new = encode(change(decode(payload), key))
        return end, b's:%d:"%s";' % (len(new), new)
    head = ARRAY_HEAD.match(data, at)
    if head:
        return _members(
            data, head.end(), int(head.group(1)), change, data[at : head.end()]
        )
    head = OBJECT_HEAD.match(data, at)
    if head:
        # O:<len>:"Class":<n>:{
        name_end, _ = _quoted(data, head, b'":')
        count = re.compile(rb"(\d+):\{").match(data, name_end)
        if count is None:
            raise NotSerialized(f"object without a member count at {name_end}")
        return _members(
            data, count.end(), int(count.group(1)), change, data[at : count.end()]
        )
    head = CUSTOM_HEAD.match(data, at)
    if head:
        # C:<len>:"Class":<len>:{<opaque>}
        name_end, _ = _quoted(data, head, b'":')
        size = re.compile(rb"(\d+):\{").match(data, name_end)
        if size is None:
            raise NotSerialized(f"custom object without a length at {name_end}")
        end = size.end() + int(size.group(1))
        if data[end : end + 1] != b"}":
            raise NotSerialized(f"custom object does not end at {end}")
        return end + 1, data[at : end + 1]
    head = ENUM_HEAD.match(data, at)
    if head:
        end, _ = _quoted(data, head, b'";')
        return end, data[at:end]
    raise NotSerialized(f"no value at {at}")


def _quoted(data: bytes, head: re.Match[bytes], closing: bytes) -> tuple[int, bytes]:
    """The `<len>` bytes after a head ending in a quote, and the offset after `closing`."""
    start = head.end()
    stop = start + int(head.group(1))
    if data[stop : stop + len(closing)] != closing:
        raise NotSerialized(f"string of the wrong length at {head.start()}")
    return stop + len(closing), data[start:stop]


def _members(
    data: bytes, at: int, count: int, change: Change, head: bytes
) -> tuple[int, bytes]:
    """`count` key/value pairs from `at` up to the closing brace."""
    parts = [head]
    for _ in range(count):
        at, key_bytes = _value(data, at, change, None)
        key = _key_name(key_bytes)
        at, value_bytes = _value(data, at, change, key)
        parts += [key_bytes, value_bytes]
    if data[at : at + 1] != b"}":
        raise NotSerialized(f"members do not end at {at}")
    parts.append(b"}")
    return at + 1, b"".join(parts)


def _key_name(serialized_key: bytes) -> str | None:
    """The name an array key or property stands for (protected/private markers removed)."""
    if serialized_key.startswith(b"i:"):
        return decode(serialized_key[2:-1])
    head = STRING_HEAD.match(serialized_key)
    if head is None:
        return None
    name = decode(serialized_key[head.end() : -2])
    # serialize() writes "\0*\0name" for protected and "\0Class\0name" for private properties.
    return name.rsplit("\0", 1)[-1]
