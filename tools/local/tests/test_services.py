from pathlib import Path

from linker_local.instance import Instance
from linker_local.services import SERVICES


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
