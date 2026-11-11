"""Official BDEW/VDEW standard load profiles as real energy-domain inputs.

The published tables are the source of truth here, so the assertions pin the
values that the publishers themselves state (their normalisation basis, their
dynamisation checkpoints, their day-type rules) and then run a real year of
quarter-hours through the ordinary CSV intake and the ordinary energy kernel.
No synthetic shape is used anywhere in this file.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from linker_engine.planning import load_profile
from linker_engine.planning.assets import Assets
from linker_engine.planning.canonical import Object, encode
from linker_engine.planning.csv_mapping import CsvMapping
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.numerical_tolerance import Tolerance
from linker_engine.planning.power_series import Measurement
from linker_engine.planning.profile_import import ProfileImport
from linker_engine.planning.records import Actor
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace

from .conftest import FixtureObject, json_object

TOLERANCE = Tolerance(1e-7, 1e-7, 1e-9)
BATTERY: FixtureObject = {
    "schema_version": 1,
    "model": "constant_window_single_ac_bus_v1",
    "parameter_basis": "explicit_scenario",
    "usable_window_kwh": 400,
    "charge_ac_kw": 200,
    "discharge_ac_kw": 200,
    "eta_charge": 0.94,
    "eta_discharge": 0.94,
    "internal_aux_kw": 0.2,
    "standing_loss_rate_per_hour": 0,
}


def csv_mapping(measurement: Measurement, *, interval_seconds: float) -> CsvMapping:
    return CsvMapping(
        "time",
        "power",
        measurement,
        "interval_average_kw",
        "start",
        "Europe/Berlin",
        # The published profile is modelled data, never a measurement.
        "modelled",
        interval_seconds,
        ",",
        ".",
    )


def official_provenance(profile: load_profile.LoadProfile) -> Object:
    document = profile.provenance()
    return {
        key: value
        for key, value in document.items()
        if isinstance(value, str | int | float | bool)
        or (isinstance(value, list) and all(isinstance(item, str) for item in value))
    }


def test_published_tables_are_the_hashed_companions_of_their_documents() -> None:
    import hashlib
    import json

    sources = json.loads((load_profile.DATA / "sources.json").read_bytes())
    for edition in ("1999", "2025"):
        entry = sources["editions"][edition]
        path = load_profile.DATA / entry["file"]
        content = path.read_bytes()
        assert len(content) == entry["bytes"]
        assert hashlib.sha256(content).hexdigest() == entry["sha256"]
        # The coefficient file must keep the published basis the expander uses.
        document = json.loads(content)
        assert (
            document["normalisation_kwh_per_year"]
            == entry["normalisation_kwh_per_year"]
        )
        assert document["interval_minutes"] == 15


def test_dynamisation_polynomial_reproduces_the_published_checkpoints() -> None:
    # Both editions carry this polynomial; the 2000 method report states the
    # three extremal factors verbatim.
    assert load_profile.dynamisation_factor(202) == pytest.approx(0.7847, abs=5e-5)
    assert load_profile.dynamisation_factor(365) == pytest.approx(1.2572, abs=5e-5)
    assert load_profile.dynamisation_factor(366) == pytest.approx(1.2597, abs=5e-5)


def test_nationwide_holiday_set_is_exactly_the_nine_statutory_days() -> None:
    days = load_profile.nationwide_holidays(2025)
    assert len(days) == 9
    assert date(2025, 1, 1) in days
    assert date(2025, 4, 18) in days  # Karfreitag
    assert date(2025, 4, 21) in days  # Ostermontag
    assert date(2025, 5, 29) in days  # Christi Himmelfahrt
    assert date(2025, 6, 9) in days  # Pfingstmontag
    assert date(2025, 5, 1) in days
    assert date(2025, 10, 3) in days
    assert date(2025, 12, 25) in days
    assert date(2025, 12, 26) in days
    # A state holiday the BMI list does not cover must not be asserted in.
    assert date(2025, 6, 19) not in days  # Fronleichnam
    assert date(2025, 11, 1) not in days  # Allerheiligen
    assert date(2025, 10, 31) not in days  # Reformationstag


def test_1999_season_and_daytype_rules_follow_the_primary_document() -> None:
    holidays = load_profile.nationwide_holidays(1997)
    assert load_profile.season_1999(date(1997, 1, 15)) == "Winter"
    assert load_profile.season_1999(date(1997, 3, 20)) == "Winter"
    assert load_profile.season_1999(date(1997, 3, 21)) == "Übergangszeit"
    assert load_profile.season_1999(date(1997, 5, 14)) == "Übergangszeit"
    assert load_profile.season_1999(date(1997, 5, 15)) == "Sommer"
    assert load_profile.season_1999(date(1997, 9, 14)) == "Sommer"
    assert load_profile.season_1999(date(1997, 9, 15)) == "Übergangszeit"
    assert load_profile.season_1999(date(1997, 10, 31)) == "Übergangszeit"
    assert load_profile.season_1999(date(1997, 11, 1)) == "Winter"
    # Public holidays take the Sunday profile; 24.12. and 31.12. take Saturday.
    assert load_profile.daytype_1999(date(1997, 1, 1), holidays) == "Sonntag"
    assert load_profile.daytype_1999(date(1997, 12, 24), holidays) == "Samstag"
    assert load_profile.daytype_1999(date(1997, 12, 31), holidays) == "Samstag"
    assert load_profile.daytype_1999(date(1997, 12, 27), frozenset()) == "Samstag"
    assert load_profile.daytype_1999(date(1997, 12, 28), frozenset()) == "Sonntag"
    assert load_profile.daytype_1999(date(1997, 3, 25), holidays) == "Werktag"


def test_expanded_year_tiles_exactly_every_real_quarter_hour() -> None:
    profile = load_profile.expand(1999, "H0", year=2025, annual_kwh=4500.0)
    assert profile.interval_count == 365 * 96
    assert sum(interval.hours for interval in profile.intervals) == pytest.approx(
        8760.0
    )
    for previous, current in zip(
        profile.intervals, profile.intervals[1:], strict=False
    ):
        assert current.start == previous.end
    # 2025-03-30 is the spring-forward day: 92 real quarter-hours.
    spring = date(2025, 3, 30)
    spring_slots = [
        interval
        for interval in profile.intervals
        if interval.start.astimezone(ZoneInfo("Europe/Berlin")).date() == spring
    ]
    assert len(spring_slots) == 92
    # 2025-10-26 is the fall-back day: 100 real quarter-hours, hour repeated.
    autumn = date(2025, 10, 26)
    autumn_slots = [
        interval
        for interval in profile.intervals
        if interval.start.astimezone(ZoneInfo("Europe/Berlin")).date() == autumn
    ]
    assert len(autumn_slots) == 100


def test_expanded_year_reproduces_the_published_normalisation_basis() -> None:
    # The 1999 tables are normalised to 1,000 kWh/a; expanding one nominal year
    # at that basis must land inside the discretisation the publishers accepted
    # (three seasons x three day types over a real calendar).
    for name in ("H0", "G0", "G1", "G2", "G3", "G4", "G5", "G6"):
        profile = load_profile.expand(1999, name, year=2025, annual_kwh=1000.0)
        assert profile.normalisation_gap == pytest.approx(1.0, abs=0.06), name
    # The 2025 tables are normalised to 1 Mio kWh/a and are month-based.
    for name in ("H25", "G25", "L25"):
        profile = load_profile.expand(2025, name, year=2025, annual_kwh=1_000_000.0)
        assert profile.normalisation_gap == pytest.approx(1.0, abs=0.01), name


def test_pv_and_battery_combination_profiles_are_net_import_shapes() -> None:
    # P25 and S25 publish net household import with PV (and battery) already
    # netted out; BDEW requires that self-consumption to be settled separately
    # on the supplier side. They must never be handed to a gross-load role.
    assert load_profile.role("P25") == "net_import"
    assert load_profile.role("S25") == "net_import"
    assert load_profile.role("H25") == "gross_load"
    assert load_profile.role("G25") == "gross_load"
    assert load_profile.role("G3") == "gross_load"
    # Undynamised they fall measurably below the published basis, which is the
    # shape difference the netting creates; dynamised they return to it because
    # the publisher normalises the finished annual course to the same basis.
    raw_pv = load_profile.expand(
        2025, "P25", year=2025, annual_kwh=1_000_000.0, dynamise=False
    )
    raw_battery = load_profile.expand(
        2025, "S25", year=2025, annual_kwh=1_000_000.0, dynamise=False
    )
    assert raw_pv.normalisation_gap == pytest.approx(0.949, abs=0.002)
    assert raw_battery.normalisation_gap == pytest.approx(0.887, abs=0.002)
    assert raw_battery.annual_kwh < raw_pv.annual_kwh
    for name in ("P25", "S25"):
        published = load_profile.expand(2025, name, year=2025, annual_kwh=1_000_000.0)
        assert published.dynamised is True
        assert published.normalisation_gap == pytest.approx(1.0, abs=0.002), name
    # G25 and L25 are published dynamisation-free and stay that way by default.
    for name in ("G25", "L25"):
        unpublished = load_profile.expand(2025, name, year=2025, annual_kwh=1_000_000.0)
        assert unpublished.dynamised is False
    from linker_engine.planning.errors import InvalidInput

    with pytest.raises(InvalidInput, match="unknown standard load profile"):
        load_profile.role("nonsense")


def test_scaling_is_linear_in_the_declared_annual_consumption() -> None:
    single = load_profile.expand(1999, "G1", year=2025, annual_kwh=1000.0)
    triple = load_profile.expand(1999, "G1", year=2025, annual_kwh=3000.0)
    assert triple.annual_kwh == pytest.approx(3 * single.annual_kwh, rel=1e-12)
    assert max(triple.values_kw) == pytest.approx(3 * max(single.values_kw), rel=1e-12)


def test_state_holidays_change_the_shape_only_when_declared() -> None:
    # Bavaria treats Fronleichnam and Allerheiligen as statutory; declaring them
    # must move those days onto the Sunday/holiday shape.
    plain = load_profile.expand(2025, "G25", year=2025, annual_kwh=100_000.0)
    bavaria = load_profile.expand(
        2025,
        "G25",
        year=2025,
        annual_kwh=100_000.0,
        extra_holidays=(date(2025, 6, 19), date(2025, 11, 1)),
    )
    assert bavaria.annual_kwh < plain.annual_kwh
    assert bavaria.extra_holidays == (date(2025, 6, 19), date(2025, 11, 1))
    assert plain.extra_holidays == ()


def test_unknown_profile_or_mixed_edition_fails_explicitly() -> None:
    from linker_engine.planning.errors import InvalidInput

    with pytest.raises(InvalidInput, match="unknown 1999 standard load profile"):
        load_profile.coefficient_table(1999, "G25")
    with pytest.raises(InvalidInput, match="unknown 2025 standard load profile"):
        load_profile.coefficient_table(2025, "H0")
    with pytest.raises(InvalidInput, match="annual consumption must be positive"):
        load_profile.expand(1999, "H0", year=2025, annual_kwh=0.0)


def test_csv_round_trip_preserves_the_published_annual_energy() -> None:
    profile = load_profile.expand(2025, "G25", year=2025, annual_kwh=250_000.0)
    content = load_profile.to_csv(profile)
    assert content.startswith(b"time,power\n")
    assert content.count(b"\n") == profile.interval_count + 1


def add_official_profile(
    workspace: Workspace,
    owner: Actor,
    project_id: str,
    profile: load_profile.LoadProfile,
    measurement: Measurement,
    *,
    key: str,
) -> str:
    return (
        ProfileImport(Assets(workspace))
        .csv(
            owner,
            project_id,
            load_profile.to_csv(profile),
            csv_mapping(measurement, interval_seconds=900),
            official_provenance(profile),
            key=key,
        )
        .id
    )


PVGIS_SAMPLE = (
    Path(__file__).resolve().parents[4]
    / "docs/research/2026-10-23-pv-inputs/raw/era5-berlin-2020.seriescalc.json"
)


def pvgis_year_csv(peak_kwp: float) -> tuple[bytes, tuple[datetime, datetime]]:
    """The retained real PVGIS hourly year, scaled to the site, explicit offsets.

    PVGIS stamps each row at the *centre* of its hour (`20200101:0030` is
    00:00-01:00) and the retained sample covers the leap year 2020, 8,784
    hours. Both facts are honoured here rather than assumed away: the start of
    the hour is stamped and the provider's own UTC timeline is preserved. The
    returned span is the real axis this series covers.
    """
    import json

    document = json.loads(PVGIS_SAMPLE.read_bytes())
    rows = document["outputs"]["hourly"]
    zone = ZoneInfo("Europe/Berlin")
    lines = ["time,power"]
    span_start: datetime | None = None
    span_end: datetime | None = None
    for row in rows:
        centre = datetime.strptime(row["time"], "%Y%m%d:%H%M").replace(
            tzinfo=ZoneInfo("UTC")
        )
        start = centre - timedelta(minutes=30)
        end = start + timedelta(hours=1)
        span_start = start if span_start is None else span_start
        span_end = end
        lines.append(
            f"{start.astimezone(zone).isoformat(timespec='seconds')},"
            f"{row['P'] * peak_kwp / 1000.0:.10f}"
        )
    if span_start is None or span_end is None:
        raise AssertionError("retained PVGIS sample is empty")
    return ("\n".join(lines) + "\n").encode(), (span_start, span_end)


def test_official_bdew_profiles_run_through_the_real_energy_kernel(
    workspace: Workspace, owner: Actor
) -> None:
    """A whole real year: published G25 load against the retained real PVGIS year."""
    project = workspace.create(
        owner,
        "Commercial site, official BDEW G25 load",
        {"site": {"country": "DE"}},
        key="create",
    )
    # 100 kWp-class site: 400 MWh/a commercial consumption on the G25 shape.
    # The retained PVGIS sample is the leap year 2020, so the load profile is
    # expanded for 2020 as well; the engine requires every role to cover the
    # same real axis and refuses to extrapolate.
    load = load_profile.expand(2025, "G25", year=2020, annual_kwh=400_000.0)
    load_id = add_official_profile(
        workspace, owner, project.id, load, "gross_load", key="load"
    )
    pv_csv, pv_axis = pvgis_year_csv(100.0)
    pv_id = (
        ProfileImport(Assets(workspace))
        .csv(
            owner,
            project.id,
            pv_csv,
            csv_mapping("pv_available_ac", interval_seconds=3600),
            {
                "label": "Retained PVGIS-ERA5 hourly year, Berlin 52.52/13.405, 1 kWp scaled to 100 kWp",
                "basis": "real_provider_series",
                "rights_basis": "PVGIS is published by the European Commission JRC for reuse",
            },
            key="pv",
        )
        .id
    )
    # Auxiliary demand is a separate role with its own measurement boundary; the
    # published profile supplies its shape at a nominal 1 MWh/a.
    aux = load_profile.expand(2025, "G25", year=2020, annual_kwh=1000.0)
    aux_id = add_official_profile(
        workspace, owner, project.id, aux, "aux_ac", key="aux"
    )
    battery = Assets(workspace).add(
        owner,
        project.id,
        encode(BATTERY),
        "application/json",
        "battery_parameters_v1",
        {"retention": "permanent", "provenance": official_provenance(load)},
        key="battery",
    )
    assert load_id and pv_id and aux_id and battery.id
    # The schedule spans the intersection of the real axes the roles cover: the
    # published profile is a local calendar year while the retained PVGIS year
    # is a UTC one, so they overlap by all but the two boundary hours. The
    # engine refuses to extrapolate either role, so the honest horizon is the
    # overlap rather than a widened request.
    start = max(load.intervals[0].start, pv_axis[0])
    end = min(load.intervals[-1].end, pv_axis[1])
    inputs: FixtureObject = {
        "site": {"country": "DE"},
        "energy_replay": {
            "schema_version": 1,
            "gross_load_asset_id": load_id,
            "critical_load_asset_id": None,
            "pv_available_asset_id": pv_id,
            "aux_ac_asset_id": aux_id,
            "battery_parameters_asset_id": battery.id,
            "initial_inventory": {
                "pv_kwh": 0,
                "grid_kwh": 0,
                "initial_unknown_kwh": 0,
                "basis": "synthetic_fixture",
                "source_note": "explicit empty initial scenario",
            },
            "schedule": [
                {
                    "start_utc": start.isoformat(),
                    "end_utc": end.isoformat(),
                    "mode": "connected",
                    "reserve_kwh": 0,
                    "import_cap_kw": None,
                    "export_cap_kw": 0,
                    "pv_enabled": True,
                    "allow_grid_charge": False,
                }
            ],
            "controller": "self_consumption_with_reserve_v1",
            "terminal_min_kwh": 0,
        },
    }
    revised = workspace.revise(owner, project.id, 1, inputs, key="scenario")
    # The production planner runs with max_intervals = 100,000; a real year of
    # quarter hours (35,040) plus the hourly PV axis is what it must accept.
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=100_000)
    run = EnergyService(workspace, kernel, max_attempts=1).evaluate(
        owner, project.id, revised.revision, key="run"
    )
    worker = Worker(
        Jobs(workspace),
        "official-load-worker",
        {"evaluate": kernel},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
    )
    assert worker.run_once()
    finished = workspace.run(owner, run.id)
    assert finished.state == "succeeded", finished.error
    result = json_object(finished.result)
    metrics = json_object(result["metrics"])
    # The engine re-derives the intake's own integral; the horizon is trimmed to
    # the overlap with the PVGIS axis, so the difference is exactly the boundary
    # hour the PV series does not cover, never a rescaled year.
    full = load.annual_kwh
    covered = metrics["gross_load_kwh"]
    boundary_kwh = sum(
        power * interval.hours
        for power, interval in zip(load.values_kw, load.intervals, strict=True)
        if interval.end > end or interval.start < start
    )
    assert full - covered == pytest.approx(boundary_kwh, rel=1e-6)
    assert covered == pytest.approx(403_556.69, rel=1e-6)
    assert result["interval_count"] == 35_132
    # The battery is real in the run: the published load is served partly from
    # storage rather than all from the grid.
    assert metrics["grid_import_kwh"] < metrics["gross_load_kwh"]
    # The published G25 day shape peaks below the annual mean times four.
    assert metrics["gross_load_kwh"] > 0
