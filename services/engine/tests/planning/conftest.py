"""Real private files and SQLite; only time and scientific fixtures are synthetic."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from linker_engine.planning.canonical import digest
from linker_engine.planning.records import Actor, Context
from linker_engine.planning.workspace import Workspace


@dataclass
class Clock:
    value: float = 100_000.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def workspace(tmp_path: Path, clock: Clock) -> Workspace:
    return Workspace(tmp_path / "private", clock=clock)


@pytest.fixture
def owner() -> Actor:
    return Actor("user", "wordpress:17")


@pytest.fixture
def context(workspace: Workspace) -> Context:
    # This proves persistence, not PV yield or an engineering model. Numerical
    # acceptance uses independent physical fixtures in the numerical modules.
    return Context(
        code_sha256=digest(b"synthetic-executor-v1"),
        models={"persistence-fixture": "1"},
        assets={"weather": workspace.blobs.put(b"frozen-fixture-weather")},
        parameters={"fixture_only": True},
    )
