import socket
from pathlib import Path

import pytest

from linker_local import objectcache
from linker_local.instance import Instance
from linker_local.objectcache import RedisError


def free_port() -> int:
    with socket.create_server(("127.0.0.1", 0)) as probe:
        port: int = probe.getsockname()[1]
        return port


def test_redis_must_be_running(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(objectcache, "REDIS_PORT", free_port())

    with pytest.raises(RedisError, match="brew services start redis"):
        objectcache.require_redis()


def test_a_listening_redis_port_is_enough(monkeypatch: pytest.MonkeyPatch) -> None:
    with socket.create_server(("127.0.0.1", 0)) as redis:
        monkeypatch.setattr(objectcache, "REDIS_PORT", redis.getsockname()[1])

        objectcache.require_redis()


def test_each_instance_keeps_to_its_own_prefix() -> None:
    instance = Instance("a", 8888, 8889, 8890, Path("/data"))

    assert objectcache.prefix(instance) == "linker_a:"
    assert (
        "define( 'WP_REDIS_PREFIX', 'linker_a:' );"
        in objectcache.wp_config_constants(instance)
    )
    assert (
        "define( 'WP_REDIS_SELECTIVE_FLUSH', true );"
        in objectcache.wp_config_constants(instance)
    )


def test_a_redis_storm_degrades_the_cache_instead_of_the_request() -> None:
    """The drop-in dies on a failed cache read unless WP_REDIS_GRACEFUL is set:
    its fail_gracefully flag defaults off, and the observed review-instance
    failure was exactly that - a Predis connection exception per dead request.
    Graceful mode logs the exception and serves the request without Redis."""
    instance = Instance("a", 8888, 8889, 8890, Path("/data"))

    assert "define( 'WP_REDIS_GRACEFUL', true );" in objectcache.wp_config_constants(
        instance
    )


def test_forget_deletes_the_instances_keys_and_nothing_else(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = tmp_path / "calls"
    cli = tmp_path / "bin" / "redis-cli"
    cli.parent.mkdir()
    # Redis --json SCAN response: cursor then keys, never an unbounded --scan.
    cli.write_text(
        "#!/bin/sh\n"
        f'echo "$@" >> "{calls}"\n'
        """case "$*" in *SCAN*) echo '["0",["linker_a:wp:options:alloptions","linker_a:wp:posts:1"]]';; *UNLINK*) echo 2;; esac\n"""
    )
    cli.chmod(0o755)
    monkeypatch.setenv("PATH", f"{cli.parent}:/usr/bin:/bin")

    assert objectcache.forget(Instance("a", 8888, 8889, 8890, tmp_path)) == 2
    port = objectcache.REDIS_PORT
    assert calls.read_text().splitlines() == [
        f"-h 127.0.0.1 -p {port} --json SCAN 0 MATCH linker_a:* COUNT 128",
        f"-h 127.0.0.1 -p {port} UNLINK linker_a:wp:options:alloptions linker_a:wp:posts:1",
    ]


def test_scan_is_bounded_and_reuse_stops_before_next_unlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import json
    from unittest.mock import Mock

    keys = [f"linker_a:{n}" for n in range(300)]
    redis = Mock(side_effect=[json.dumps(["3", keys]), "128"])
    monkeypatch.setattr(objectcache, "_redis_cli", redis)
    # Before SCAN, before first batch, then a newly registered owner appears.
    permitted = Mock(side_effect=[True, True, False])
    with pytest.raises(RedisError, match="reused"):
        objectcache.forget(Instance("a", 1, 2, 3, tmp_path), permitted=permitted)
    assert len(redis.call_args_list) == 2
    assert len(redis.call_args_list[1].args) == 129


def test_foreign_scan_key_is_never_unlinked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import Mock

    redis = Mock(return_value='["0",["linker_b:secret"]]')
    monkeypatch.setattr(objectcache, "_redis_cli", redis)
    with pytest.raises(RedisError, match="foreign key"):
        objectcache.forget(Instance("a", 1, 2, 3, tmp_path))
    assert redis.call_count == 1
