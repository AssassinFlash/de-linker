"""The seam: one local instance, one host, and the commands each produces.

No WordPress is started. What these tests can find is exactly what a drill
would otherwise find late: a command built for the wrong machine, a path
escaping the WordPress root, a cache-buster that is not appended.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from linker_cutover.target import (
    HOST,
    PLUGINS,
    CutoverError,
    Target,
    remote_target,
    wp_prefix_for,
)


def _local(root: Path) -> Target:
    """A local target built by hand, so the tests need no instance registry."""
    return Target(
        label="local:test",
        root=str(root),
        base_url="http://127.0.0.1:9999",
        prefix=("php", "-c", "php.ini", "wp", f"--path={root}"),
        shell_prefix=None,
        rsync_remote=None,
    )


def test_the_remote_target_reaches_the_host_read_write() -> None:
    """A cutover writes; a read-only command builder would fail at the first write."""
    target = remote_target()
    assert target.label == HOST
    assert target.base_url == "https://de-linker.com"
    assert target.shell_prefix == ("ssh", "-o", "BatchMode=yes", HOST, "bash -c")
    assert (
        target.rsync_remote
        == f"{HOST}:/home/u388076051/domains/de-linker.com/public_html"
    )
    # WP-CLI runs on the host, from the WordPress root, at the path
    # tools/pull/src/linker_pull/live.py recorded.
    assert (
        target.prefix[-1]
        == "cd /home/u388076051/domains/de-linker.com/public_html && /usr/local/bin/wp"
    )
    # WP-CLI is the host's own binary, reached through the ssh command above;
    # the two are different seams and neither is the other's alias.
    assert "/usr/local/bin/wp" in target.prefix[-1]
    assert target.root in target.prefix[-1]


def test_a_relative_path_resolves_under_the_root_and_an_absolute_one_is_refused(
    tmp_path: Path,
) -> None:
    """A path outside the root would let a removal step delete something else."""
    target = _local(tmp_path)
    assert target.path_of(PLUGINS) == str(tmp_path / PLUGINS)
    for escaping in ("/etc/passwd", "../../etc", "wp-content/../.."):
        with pytest.raises(CutoverError):
            target.path_of(escaping)


def test_the_wp_prefix_is_quoted_for_a_caller_that_splits_it() -> None:
    """tools/migrate gets `--wp <prefix>` as one string and shlex-splits it back."""
    import shlex

    target = _local(Path("/tmp/a root with spaces"))
    parts = shlex.split(wp_prefix_for(target))
    assert parts == list(target.prefix)
    assert parts[-1].endswith("a root with spaces")


def test_the_cache_buster_is_appended_to_every_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Production serves through LiteSpeed's cache; an uncache-busted read is not evidence."""
    seen: list[str] = []

    class _Response:
        status = 200

        def read(self) -> bytes:
            return b"ok"

        def __enter__(self) -> _Response:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def fake_urlopen(request: object, timeout: int = 0) -> _Response:
        seen.append(request.full_url)  # type: ignore[attr-defined]
        return _Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    target = _local(tmp_path)
    status, body = target.http("/de/produkte/", cache_buster="abc")
    assert (status, body) == (200, "ok")
    assert seen == ["http://127.0.0.1:9999/de/produkte/?cbq=abc"]
    target.http("/?s=x", cache_buster="abc")
    assert seen[-1].endswith("?s=x&cbq=abc")
