"""Real private files and SQLite; only time and scientific fixtures are synthetic."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pytest

from linker_engine.planning.canonical import digest
from linker_engine.planning.power_series import MEASUREMENTS, Measurement
from linker_engine.planning.records import Actor, Context
from linker_engine.planning.workspace import Workspace

# Mutable protocol fixtures include deliberate invalid values. Their assertions
# inspect the serialized fields; production retains its stricter Json model.
type FixtureObject = dict[str, Any]


def json_object(value: object) -> FixtureObject:
    """Read a real serialized result before assertions on its dynamic fields."""
    assert isinstance(value, dict)
    assert all(isinstance(key, str) for key in value)
    return value


def mapping_role(value: str) -> Measurement:
    assert value in MEASUREMENTS
    return cast(Measurement, value)


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
