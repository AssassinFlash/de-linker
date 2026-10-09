"""Changing strings inside PHP-serialized values.

Every rewritten value is also handed to PHP's own unserialize() when a PHP is
available ($PHP, as `just test` sets it, or `php`), so "still valid" means
what WordPress will see, not what this module believes.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess

import pytest

from linker_pull.phpserial import looks_serialized, rewrite

PHP = shutil.which(os.environ.get("PHP", "php"))


def php_unserialize(serialized: str) -> object:
    """PHP's unserialize() of `serialized`, as JSON; fails the test if PHP cannot read it."""
    if PHP is None:
        pytest.skip("no PHP to check the result with")
    result = subprocess.run(
        [
            PHP,
            "-r",
            "$v = unserialize(stream_get_contents(STDIN)); if ($v === false) exit(1);"
            " echo json_encode($v, JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);",
        ],
        input=serialized.encode(),
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, f"PHP cannot unserialize {serialized!r}"
    return json.loads(result.stdout)


def upper(text: str, key: str | None) -> str:
    return text.upper()


def test_strings_change_and_their_byte_lengths_follow() -> None:
    # "jürgen" is 6 characters and 7 bytes; serialize() counts bytes.
    serialized = 'a:2:{s:4:"name";s:7:"jürgen";s:4:"list";a:1:{i:0;s:3:"abc";}}'

    result = rewrite(
        serialized, lambda text, key: text.replace("jürgen", "customer-18")
    )

    assert (
        result == 'a:2:{s:4:"name";s:11:"customer-18";s:4:"list";a:1:{i:0;s:3:"abc";}}'
    )
    assert php_unserialize(result) == {"name": "customer-18", "list": ["abc"]}


def test_the_change_sees_the_key_a_value_is_stored_under() -> None:
    serialized = 'a:3:{s:7:"api_key";s:6:"secret";i:7;s:1:"x";s:5:"model";s:2:"ds";}'
    seen: list[tuple[str, str | None]] = []

    def record(text: str, key: str | None) -> str:
        seen.append((text, key))
        return "" if key == "api_key" else text

    result = rewrite(serialized, record)

    assert ("secret", "api_key") in seen
    assert ("x", "7") in seen
    assert ("api_key", None) in seen  # keys are strings too
    assert result is not None
    assert php_unserialize(result) == {"api_key": "", "7": "x", "model": "ds"}


def test_objects_with_protected_and_private_properties() -> None:
    serialized = 'O:8:"stdClass":1:{s:3:"url";s:21:"https://de-linker.com";}'
    names: list[str | None] = []

    def record(text: str, key: str | None) -> str:
        names.append(key)
        return text.replace("https://de-linker.com", "http://127.0.0.1:8106")

    result = rewrite(serialized, record)

    assert result == 'O:8:"stdClass":1:{s:3:"url";s:21:"http://127.0.0.1:8106";}'
    assert php_unserialize(result) == {"url": "http://127.0.0.1:8106"}
    names.clear()
    protected = 'O:3:"Foo":1:{s:7:"\0*\0mail";s:1:"a";}'
    rewrite(protected, record)
    assert "mail" in names


def test_scalars_null_references_and_enums_are_copied() -> None:
    serialized = "a:5:{i:0;N;i:1;b:1;i:2;i:-3;i:3;d:0.5;i:4;R:2;}"

    assert rewrite(serialized, upper) == serialized


def test_a_serialized_string_inside_a_string_is_the_caller_s_to_open() -> None:
    inner = 'a:1:{s:5:"email";s:13:"jdoe@kunde.de";}'
    outer = f's:{len(inner)}:"{inner}";'

    def nested(text: str, key: str | None) -> str:
        again = rewrite(
            text, lambda s, k: s.replace("jdoe@kunde.de", "customer-18@example.test")
        )
        return again if again is not None else text

    result = rewrite(outer, nested)

    assert result is not None
    assert (
        php_unserialize(result) == 'a:1:{s:5:"email";s:24:"customer-18@example.test";}'
    )


@pytest.mark.parametrize(
    "text",
    [
        "plain text",
        'a:1:{s:3:"url";s:99:"short";}',  # wrong length
        'a:2:{s:1:"a";s:1:"b";}',  # fewer members than declared
        'a:1:{s:1:"a";s:1:"b";}trailing',
        '{"json": true}',
        's:5:"hello"',  # no semicolon
    ],
)
def test_what_is_not_one_serialized_value_is_none(text: str) -> None:
    assert rewrite(text, upper) is None


def test_looks_serialized_is_a_cheap_prefilter() -> None:
    assert looks_serialized('a:1:{i:0;s:1:"a";}')
    assert looks_serialized('s:1:"a";')
    assert looks_serialized('O:8:"stdClass":0:{}')
    assert not looks_serialized("i:5;")  # holds no string
    assert not looks_serialized("a: list")
    assert not looks_serialized("")
