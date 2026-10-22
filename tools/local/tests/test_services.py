from pathlib import Path

import pytest

from linker_local.instance import Instance
from linker_local.processes import ProcessError
from linker_local.services import (
    SERVICES,
    genie_environment,
    genie_index,
    planner_environment,
)


def test_each_service_has_its_own_port_log_and_option() -> None:
    instance = Instance("a", 8888, 8889, 8890, Path("/data"))

    assert [(s.name, s.port(instance), s.option) for s in SERVICES] == [
        ("engine", 8889, "linker_engine_url"),
        ("genie", 8890, "linker_genie_url"),
    ]
    engine = SERVICES[0].process(instance)
    assert (engine.pid_file, engine.log_file) == (
        Path("/data/a/run/engine.pid"),
        Path("/data/a/logs/engine.log"),
    )
    assert SERVICES[0].app == "linker_engine.application:app"


def test_planner_config_is_private_isolated_and_preserves_operator_changes(
    tmp_path: Path,
) -> None:
    import json
    import stat

    a = Instance("a", 8888, 8889, 8890, tmp_path)
    b = Instance("b", 8891, 8892, 8893, tmp_path)
    path_a = Path(planner_environment(a)["LINKER_PLANNER_CONFIG"])
    path_b = Path(planner_environment(b)["LINKER_PLANNER_CONFIG"])
    values_a = json.loads(path_a.read_bytes())
    values_b = json.loads(path_b.read_bytes())
    assert values_a["directory"] != values_b["directory"]
    assert values_a["directory"] == str(a.dir / "planner/workspace")
    assert values_a["max_csv_bytes"] < values_a["max_body_bytes"]
    assert values_a["schema_version"] == 1
    assert stat.S_IMODE(path_a.stat().st_mode) == 0o600
    changed = {**values_a, "max_page_size": 17}
    path_a.write_text(json.dumps(changed))
    assert planner_environment(a)["LINKER_PLANNER_CONFIG"] == str(path_a)
    assert json.loads(path_a.read_bytes()) == changed


def test_each_instance_logs_genie_turns_in_its_own_directory() -> None:
    a = Instance("a", 8888, 8889, 8890, Path("/data"))
    b = Instance("b", 8891, 8892, 8893, Path("/data"))

    index = Path("/data/index/builds/v/index.sqlite")

    assert genie_environment(a, index, "t") == {
        "GENIE_WP_URL": "http://127.0.0.1:8888",
        "GENIE_LOG": "/data/a/genie/turns.sqlite",
        "GENIE_INDEX": "/data/index/builds/v/index.sqlite",
        "GENIE_SERVICE_TOKEN": "t",
        "LINKER_GENIE_WORK_MODE": "enforce",
        "LINKER_GENIE_WORK_PATH": "/data/a/genie/private/work.sqlite",
    }
    assert (
        genie_environment(a, index, "t")["GENIE_LOG"]
        != genie_environment(b, index, "t")["GENIE_LOG"]
    )


def _builds(root: Path, *versions: str) -> Path:
    for version in versions:
        directory = root / "index" / "builds" / version
        directory.mkdir(parents=True)
        (directory / "index.sqlite").write_bytes(b"")
    return root


def test_genie_reads_the_newest_build(tmp_path: Path) -> None:
    data = _builds(
        tmp_path, "20261011T000000Z-repair", "20261016T072222Z", "20261016T065329Z"
    )
    (data / "index" / "builds" / "20261099T000000Z-empty").mkdir()

    index = genie_index({"LINKER_DATA": str(data)})

    assert index.path == data / "index/builds/20261016T072222Z/index.sqlite"
    assert index.line() == (
        f"genie index {index.path} (build 20261016T072222Z, the newest here)"
    )


def test_an_explicit_genie_index_wins(tmp_path: Path) -> None:
    data = _builds(tmp_path, "20261016T072222Z")
    chosen = tmp_path / "other.sqlite"
    chosen.write_bytes(b"")

    index = genie_index({"LINKER_DATA": str(data), "GENIE_INDEX": str(chosen)})

    assert (index.path, index.source) == (chosen, "GENIE_INDEX")


def test_an_explicit_genie_index_that_is_missing_fails(tmp_path: Path) -> None:
    with pytest.raises(ProcessError, match="is not a file"):
        genie_index({"GENIE_INDEX": str(tmp_path / "missing.sqlite")})


def test_no_index_fails_and_says_how_to_get_one(tmp_path: Path) -> None:
    with pytest.raises(ProcessError, match="no Genie document index") as error:
        genie_index({"LINKER_DATA": str(tmp_path)})

    assert "rsync -a linker-services:/opt/linker-genie/index/current/" in str(
        error.value
    )
    assert "just index" in str(error.value)
