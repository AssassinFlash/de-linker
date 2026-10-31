"""instances.toml: which instances exist on this Mac and the ports each one owns.

The registry lives in the data root, not in the repository: every checkout
(one worktree per ticket) shares the same MySQL server and the same ports, so
only a registry per machine can keep two instances from taking the same port.
"""

from __future__ import annotations

import fcntl
import os
import tomllib
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

from linker_local.instance import SHARED, Instance, check_name
from linker_local.processes import port_is_free

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
        with _machine_lock():
            if (self.root / ".lifecycle" / f"{name}.retiring.json").exists():
                raise RuntimeError(f"{name} retirement must finish before reuse")
            instances = self._read()
            if name in instances:
                return instances[name]
            taken = _ports(instances.values())
            if self.root.resolve() != SHARED.resolve():
                # Another data root (a test run's) still shares this Mac's ports.
                taken |= _ports(Registry(SHARED)._read().values())
            port, engine_port, genie_port = _free_ports(3, taken)
            instances[name] = Instance(name, port, engine_port, genie_port, self.root)
            self._write(instances)
            return instances[name]

    def unregister(self, instance: Instance) -> None:
        """Remove only the registration the caller actually retired."""
        with _machine_lock():
            instances = self._read()
            if instances.get(instance.name) not in (None, instance):
                raise RuntimeError("instance registration changed during retirement")
            instances.pop(instance.name, None)
            self._write(instances)

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
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.file.with_suffix(".toml.tmp")
        temporary.write_text("".join(lines), encoding="utf-8")
        os.replace(temporary, self.file)


@contextmanager
def _machine_lock() -> Iterator[None]:
    """Serialise allocations on this Mac: two checkouts may run `just up` at once."""
    SHARED.mkdir(parents=True, exist_ok=True)
    with (SHARED / "instances.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _ports(instances: Iterable[Instance]) -> set[int]:
    return {
        port
        for instance in instances
        for port in (instance.port, instance.engine_port, instance.genie_port)
    }


def _free_ports(count: int, taken: set[int]) -> list[int]:
    """The first `count` ports from FIRST_PORT up that are neither taken nor in use."""
    ports: list[int] = []
    for port in range(FIRST_PORT, LAST_PORT + 1):
        if port not in taken and port_is_free(port):
            ports.append(port)
            if len(ports) == count:
                return ports
    raise RuntimeError(f"no {count} free ports between {FIRST_PORT} and {LAST_PORT}")
