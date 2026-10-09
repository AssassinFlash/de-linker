"""instances.toml: which instances exist on this Mac and the ports each one owns.

The registry lives in the data root, not in the repository: every checkout
(one worktree per ticket) shares the same MySQL server and the same ports, so
only a registry per machine can keep two instances from taking the same port.
"""

from __future__ import annotations

import fcntl
import os
import socket
import tomllib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from linker_local.instance import Instance, check_name

# The first port tried, wp-env's default (8888); like `wp-env --auto-port`, the
# allocation scans upward from it to the next free ports (@wordpress/env README,
# read via Apify on 2026-10-09).
FIRST_PORT = 8888
# The last of the User Ports (RFC 6335 §6, read via Apify on 2026-10-09); above
# it are the dynamic ports the system hands out to outgoing connections.
LAST_PORT = 49151

HEADER = (
    "# Local WordPress instances of this Mac, written by `linker-local up`.\n"
    "# One table per instance: the ports it owns. Its database is linker_<name>,\n"
    "# its files are in the directory <name>/ next to this file.\n"
)


class Registry:
    """The instances recorded in `<root>/instances.toml`."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.file = root / "instances.toml"

    def all(self) -> list[Instance]:
        return list(self._read().values())

    def get(self, name: str) -> Instance | None:
        return self._read().get(name)

    def register(self, name: str) -> Instance:
        """Return the instance called `name`, allocating its ports if it is new."""
        check_name(name)
        with self._locked():
            instances = self._read()
            if name in instances:
                return instances[name]
            taken = {
                port
                for instance in instances.values()
                for port in (instance.port, instance.engine_port, instance.genie_port)
            }
            port, engine_port, genie_port = _free_ports(3, taken)
            instances[name] = Instance(name, port, engine_port, genie_port, self.root)
            self._write(instances)
            return instances[name]

    def _read(self) -> dict[str, Instance]:
        if not self.file.exists():
            return {}
        with self.file.open("rb") as handle:
            data = tomllib.load(handle)
        instances = {}
        for name, entry in data.items():
            check_name(name)
            instances[name] = Instance(
                name,
                int(entry["port"]),
                int(entry["engine_port"]),
                int(entry["genie_port"]),
                self.root,
            )
        return instances

    def _write(self, instances: dict[str, Instance]) -> None:
        lines = [HEADER]
        for instance in sorted(instances.values(), key=lambda item: item.name):
            # check_name() admits only bare-key characters, so the name needs no quoting.
            lines.append(f"\n[{instance.name}]\n")
            lines.append(f"port = {instance.port}\n")
            lines.append(f"engine_port = {instance.engine_port}\n")
            lines.append(f"genie_port = {instance.genie_port}\n")
        temporary = self.file.with_suffix(".toml.tmp")
        temporary.write_text("".join(lines), encoding="utf-8")
        os.replace(temporary, self.file)

    @contextmanager
    def _locked(self) -> Iterator[None]:
        """Serialise registrations: two checkouts may run `just up` at once."""
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root / "instances.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)


def _free_ports(count: int, taken: set[int]) -> list[int]:
    """The first `count` ports from FIRST_PORT up that are neither taken nor in use."""
    ports: list[int] = []
    for port in range(FIRST_PORT, LAST_PORT + 1):
        if port not in taken and port_is_free(port):
            ports.append(port)
            if len(ports) == count:
                return ports
    raise RuntimeError(f"no {count} free ports between {FIRST_PORT} and {LAST_PORT}")


def port_is_free(port: int) -> bool:
    """Whether a server can listen on 127.0.0.1:port.

    Nothing may answer there; a connection attempt also finds a server on
    *:port. The address must then bind as servers bind it, with SO_REUSEADDR
    (PHP's main/network.c and uvicorn's config.py both set it; read via Apify
    on 2026-10-09), which disregards the connections of a just-stopped
    server that are still in TIME_WAIT.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            return False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True
