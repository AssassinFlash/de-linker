from pathlib import Path

import pytest

from linker_local.cli import main


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
