"""The address rewrite moves every cited revision; the load renews what it can.

`Publication::revision()` hashes the record including its citation URL, so the
search-replace that makes the copy's addresses local invalidates every recorded
figure binding and every recorded declaration document version. Binding alone
is additive and leaves them stale, which is what "the feed serves no facts and
no compatibility" looked like on a pulled instance.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import cast

from linker_pull import load
from linker_pull.load import WpCli


class FakeWp:
    """Records the WP-CLI commands the binding step runs."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def run(self, *args: str, stdin: Iterator[bytes] | None = None) -> str:
        self.calls.append(args)
        return ""


def test_the_binding_step_renews_the_versions_the_rewrite_moved() -> None:
    wp = FakeWp()
    said: list[str] = []

    load._bind_publication(  # noqa: SLF001
        cast(WpCli, wp), said.append, ["linker-commerce/linker-commerce.php"]
    )

    assert wp.calls == [
        ("linker-commerce", "publication", "bind-figures"),
        ("linker-commerce", "publication", "repair-bindings"),
    ]
    assert said == [
        "publication: binding this copy's figure and FAQ revisions",
        "publication: renewing unchanged evidence versions",
    ]


def test_an_instance_without_our_plugin_binds_and_renews_nothing() -> None:
    wp = FakeWp()

    load._bind_publication(  # noqa: SLF001
        cast(WpCli, wp), lambda _: None, ["fake-licensed/fake-licensed.php"]
    )

    assert wp.calls == []
