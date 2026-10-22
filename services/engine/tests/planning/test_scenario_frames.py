"""Raw measurement boundaries cannot be silently reclassified by the engine."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from linker_engine.planning.canonical import digest, encode
from linker_engine.planning.errors import InvalidInput
from linker_engine.planning.interval import regular_intervals
from linker_engine.planning.operating_limits import OperatingLimits
from linker_engine.planning.power_series import PowerSeries
from linker_engine.planning.scenario_frames import scenario_frames
from linker_engine.planning.series_source import SeriesSource


def profiles() -> tuple[PowerSeries, PowerSeries, PowerSeries]:
    axis = regular_intervals(
        datetime(2024, 1, 1, tzinfo=UTC),
        datetime(2024, 1, 1, 1, tzinfo=UTC),
        timedelta(hours=1),
    )
    source = SeriesSource(
        digest(b"explicit synthetic fixture"),
        "synthetic",
        "UTC",
        3600,
        encode({"fixture_only": True}),
    )
    return (
        PowerSeries(axis, (5,), "gross_load", source),
        PowerSeries(axis, (3,), "pv_available_ac", source),
        PowerSeries(axis, (0.1,), "aux_ac", source),
    )


def test_aligned_physical_boundaries_are_preserved() -> None:
    load, pv, aux = profiles()
    conditions = OperatingLimits("connected", 0, 10, 0, True, False)
    frame = scenario_frames(load, pv, aux, (conditions,))[0]
    assert frame.load_kw == 5 and frame.pv_potential_kw == 3 and frame.aux_ac_kw == 0.1
    assert frame.limits == conditions


def test_net_import_cannot_be_used_as_gross_load() -> None:
    load, pv, aux = profiles()
    conditions = OperatingLimits("connected", 0, 10, 0, True, False)
    with pytest.raises(InvalidInput, match="net import"):
        scenario_frames(replace(load, measurement="net_import"), pv, aux, (conditions,))


def test_measured_curtailed_pv_cannot_be_called_available_potential() -> None:
    load, pv, aux = profiles()
    conditions = OperatingLimits("connected", 0, 10, 0, True, False)
    with pytest.raises(InvalidInput, match="available AC"):
        scenario_frames(
            load, replace(pv, measurement="pv_generation_ac"), aux, (conditions,)
        )


def test_mode_schedule_cannot_be_applied_to_a_different_time_axis() -> None:
    load, pv, aux = profiles()
    with pytest.raises(InvalidInput, match="exact interval axis"):
        scenario_frames(load, pv, aux, ())
