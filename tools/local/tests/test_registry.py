import socket
from pathlib import Path

import pytest

from linker_local import registry
from linker_local.registry import FIRST_PORT, Registry, port_is_free


@pytest.fixture
def busy(monkeypatch: pytest.MonkeyPatch) -> set[int]:
    """Ports the fake port_is_free() reports as in use, so tests ignore this Mac's ports."""
    ports: set[int] = set()
    monkeypatch.setattr(registry, "port_is_free", lambda port: port not in ports)
    return ports


def test_a_new_instance_gets_the_first_three_free_ports(
    tmp_path: Path, busy: set[int]
) -> None:
    instance = Registry(tmp_path).register("a")

    assert (instance.port, instance.engine_port, instance.genie_port) == (
        FIRST_PORT,
        FIRST_PORT + 1,
        FIRST_PORT + 2,
    )
    assert instance.dir == tmp_path / "a"


def test_instances_never_share_a_port(tmp_path: Path, busy: set[int]) -> None:
    first = Registry(tmp_path).register("a")
    second = Registry(tmp_path).register("b")

    first_ports = {first.port, first.engine_port, first.genie_port}
    second_ports = {second.port, second.engine_port, second.genie_port}
    assert first_ports.isdisjoint(second_ports)
    assert second.port == FIRST_PORT + 3


def test_skips_ports_another_program_uses(tmp_path: Path, busy: set[int]) -> None:
    busy.update({FIRST_PORT, FIRST_PORT + 2})

    instance = Registry(tmp_path).register("a")

    assert (instance.port, instance.engine_port, instance.genie_port) == (
        FIRST_PORT + 1,
        FIRST_PORT + 3,
        FIRST_PORT + 4,
    )


def test_registering_again_keeps_the_ports(tmp_path: Path, busy: set[int]) -> None:
    first = Registry(tmp_path).register("a")
    busy.add(first.port)  # the instance's own server is running now

    assert Registry(tmp_path).register("a") == first


def test_the_registry_is_kept_in_instances_toml(tmp_path: Path, busy: set[int]) -> None:
    Registry(tmp_path).register("b")
    Registry(tmp_path).register("a")

    reread = Registry(tmp_path)
    assert [
        instance.name for instance in sorted(reread.all(), key=lambda i: i.name)
    ] == ["a", "b"]
    assert reread.get("missing") is None
    text = (tmp_path / "instances.toml").read_text()
    assert f"[b]\nport = {FIRST_PORT}\n" in text


def test_refuses_a_name_that_cannot_name_a_database(
    tmp_path: Path, busy: set[int]
) -> None:
    with pytest.raises(ValueError):
        Registry(tmp_path).register("Bad-Name")
    assert not (tmp_path / "instances.toml").exists()


def test_a_listening_port_is_not_free() -> None:
    with socket.create_server(("127.0.0.1", 0)) as server:
        assert not port_is_free(server.getsockname()[1])


def test_a_port_whose_server_stopped_is_free_while_its_connections_are_in_time_wait() -> (
    None
):
    with socket.create_server(("127.0.0.1", 0)) as server:
        port = server.getsockname()[1]
        with socket.create_connection(("127.0.0.1", port)) as client:
            accepted, _ = server.accept()
            # The server side closes first, so its end of the connection waits in TIME_WAIT.
            accepted.close()
            client.recv(1)
    with socket.socket() as plain:
        with pytest.raises(OSError):
            plain.bind(
                ("127.0.0.1", port)
            )  # without SO_REUSEADDR the port still looks taken

    assert port_is_free(port)
