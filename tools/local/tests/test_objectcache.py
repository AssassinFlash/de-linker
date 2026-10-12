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
    # A stand-in for redis-cli: SCAN answers two keys of the prefix, every call is logged.
    cli.write_text(
        "#!/bin/sh\n"
        f'echo "$@" >> "{calls}"\n'
        'case "$*" in *--scan*) printf "linker_a:wp:options:alloptions\\nlinker_a:wp:posts:1\\n";; esac\n'
    )
    cli.chmod(0o755)
    monkeypatch.setenv("PATH", f"{cli.parent}:/usr/bin:/bin")

    objectcache.forget(Instance("a", 8888, 8889, 8890, tmp_path))

    port = objectcache.REDIS_PORT
    assert calls.read_text().splitlines() == [
        f"-h 127.0.0.1 -p {port} --scan --pattern linker_a:*",
        f"-h 127.0.0.1 -p {port} DEL linker_a:wp:options:alloptions linker_a:wp:posts:1",
    ]
