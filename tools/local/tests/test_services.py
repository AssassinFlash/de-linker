from pathlib import Path

from linker_local.instance import Instance
from linker_local.services import SERVICES, genie_environment


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


def test_each_instance_logs_genie_turns_in_its_own_directory() -> None:
    a = Instance("a", 8888, 8889, 8890, Path("/data"))
    b = Instance("b", 8891, 8892, 8893, Path("/data"))

    assert genie_environment(a) == {
        "GENIE_WP_URL": "http://127.0.0.1:8888",
        "GENIE_LOG": "/data/a/genie/turns.sqlite",
    }
    assert genie_environment(a)["GENIE_LOG"] != genie_environment(b)["GENIE_LOG"]
