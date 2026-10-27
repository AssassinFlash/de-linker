"""Bounded route-cache probe: real in-memory SQLite, hash-checked memory bytes.

No site, process, on-disk database, runtime config, or source is modified.
Uses the pinned project's actual Workspace enqueue and Jobs.claim methods.
"""

from __future__ import annotations

import json
import importlib.abc
import importlib.util
import sqlite3
import subprocess
import sys
from contextlib import contextmanager

PIN = "af4aa66e9f4994efcbe2159f428a93cc9007c71a"


class PinnedPlanning(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Review immutable git bytes even while the owner repairs the working tree."""

    def find_spec(self, fullname, path=None, target=None):
        prefix = "linker_engine.planning"
        if fullname == prefix or fullname.startswith(prefix + "."):
            return importlib.util.spec_from_loader(
                fullname, self, is_package=fullname == prefix,
            )
        return None

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        suffix = module.__name__.removeprefix("linker_engine.planning")
        source_path = "services/engine/src/linker_engine/planning/" + (
            "__init__.py" if not suffix else suffix[1:].replace(".", "/") + ".py"
        )
        content = subprocess.check_output(["git", "show", PIN + ":" + source_path])
        exec(compile(content, PIN + ":" + source_path, "exec"), module.__dict__)


sys.meta_path.insert(0, PinnedPlanning())

from linker_engine.planning.canonical import digest
from linker_engine.planning.errors import VersionUnavailable
from linker_engine.planning.execution_identity import EvaluationRouting, execution_key
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.records import Actor, Context
from linker_engine.planning.schema import SCHEMA
from linker_engine.planning.storage import Blobs
from linker_engine.planning.workspace import Workspace


class MemoryBlobs(Blobs):
    def __init__(self):
        self.values = {}

    def put(self, content):
        sha256 = digest(content)
        self.values[sha256] = content
        return sha256

    def read(self, sha256):
        content = self.values.get(sha256)
        if content is None or digest(content) != sha256:
            raise VersionUnavailable("pinned content unavailable or hash mismatch")
        return content


class MemoryDatabase:
    def __init__(self):
        self.connection = sqlite3.connect(":memory:", isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript(SCHEMA)

    @contextmanager
    def transaction(self):
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield self.connection
            self.connection.commit()
        except BaseException:
            self.connection.rollback()
            raise

    @contextmanager
    def read(self):
        self.connection.execute("BEGIN")
        try:
            yield self.connection
            self.connection.commit()
        except BaseException:
            self.connection.rollback()
            raise


workspace = Workspace.__new__(Workspace)
workspace.database = MemoryDatabase()
workspace.blobs = MemoryBlobs()
workspace.clock = lambda: 100_000.0
owner = Actor("user", "synthetic-spec-review")
context = Context(
    code_sha256=digest(b"synthetic-route-runtime"),
    models={"route-probe": "1"},
    assets={},
    parameters={"fixture_only": True},
)
project = workspace.create(owner, "Routing probe", {"fixture_only": True}, key="p")
run = workspace.evaluate(owner, project.id, 1, context, key="run", max_attempts=2)
actual_key = execution_key(context.document())
wrong_key = digest(b"no-executable-with-this-key")
assert wrong_key != actual_key
with workspace.database.transaction() as connection:
    connection.execute("UPDATE evaluation_routes SET execution_sha256=?", (wrong_key,))

jobs = Jobs(workspace)
claims = [
    jobs.claim(
        "matching-worker", kinds=("evaluate",), lease_seconds=30,
        routing=EvaluationRouting(actual_key, 8),
    )
    for _ in range(5)
]
with workspace.database.read() as connection:
    state, attempt, route = tuple(connection.execute(
        "SELECT state, attempt, execution_sha256 FROM jobs "
        "JOIN evaluation_routes ON evaluation_routes.job_id=jobs.id"
    ).fetchone())
assert all(claim is None for claim in claims)
assert (state, attempt, route) == ("queued", 0, wrong_key)
print(json.dumps({
    "pin": "af4aa66e9f4994efcbe2159f428a93cc9007c71a",
    "matching_polls": len(claims),
    "leases": 0,
    "state": state,
    "attempt": attempt,
    "wrong_route_unchanged": route == wrong_key,
}))

# Control: remove only the derived route. The same immutable request now leases.
with workspace.database.transaction() as connection:
    connection.execute("DELETE FROM evaluation_routes")
lease = jobs.claim(
    "matching-worker", kinds=("evaluate",), lease_seconds=30,
    routing=EvaluationRouting(actual_key, 8),
)
assert lease is not None and lease.run_id == run.id and lease.attempt == 1
print(json.dumps({"control_after_cache_removal": "leased", "attempt": lease.attempt}))
workspace.database.connection.close()
