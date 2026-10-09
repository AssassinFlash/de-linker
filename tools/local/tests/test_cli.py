import socket
import sys
from pathlib import Path

import pytest

from linker_local import cli, objectcache
from linker_local.cli import main
from linker_local.registry import Registry


@pytest.fixture(autouse=True)
def empty_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("LINKER_LOCAL_HOME", str(tmp_path))
    return tmp_path


def test_an_invalid_name_is_refused_before_anything_is_made(
    empty_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["up", "Bad-Name"]) == 1

    assert "not an instance name" in capsys.readouterr().err
    assert list(empty_home.iterdir()) == []


@pytest.mark.parametrize("command", ["down", "reset", "login", "serve", "wp"])
def test_commands_on_an_unknown_instance_say_how_to_create_it(
    command: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([command, "nope"]) == 1

    assert "`just up nope`" in capsys.readouterr().err


def test_status_without_instances(
    empty_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["status"]) == 0

    assert capsys.readouterr().out == f"no instances in {empty_home}\n"


def test_a_missing_snapshot_is_refused_before_anything_is_made(
    empty_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["up", "a", "--snapshot", str(empty_home / "missing")]) == 1

    assert "has none of plugins/, themes/, uploads/" in capsys.readouterr().err
    assert list(empty_home.iterdir()) == []


@pytest.fixture
def redis_down(monkeypatch: pytest.MonkeyPatch) -> None:
    """PHP is there, Redis is not."""
    monkeypatch.setattr(cli, "require_php", lambda: Path(sys.executable))
    with socket.create_server(("127.0.0.1", 0)) as probe:
        unused = probe.getsockname()[1]
    monkeypatch.setattr(objectcache, "REDIS_PORT", unused)


def test_without_redis_up_registers_nothing(
    empty_home: Path, redis_down: None, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["up", "a"]) == 1

    assert "Redis is not running" in capsys.readouterr().err
    assert Registry(empty_home).all() == []


def test_without_redis_reset_deletes_nothing(
    empty_home: Path, redis_down: None, capsys: pytest.CaptureFixture[str]
) -> None:
    (empty_home / "instances.toml").write_text(
        "[a]\nport = 1\nengine_port = 2\ngenie_port = 3\n"
    )
    kept = empty_home / "a" / "wordpress" / "index.php"
    kept.parent.mkdir(parents=True)
    kept.write_text("<?php")

    assert main(["reset", "a"]) == 1

    assert "Redis is not running" in capsys.readouterr().err
    assert kept.exists()
