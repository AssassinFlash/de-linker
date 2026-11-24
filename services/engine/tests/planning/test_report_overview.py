from datetime import UTC, datetime

import pytest

from linker_engine.planning.report_overview import calendar_totals, replay_months
from linker_engine.planning.records import Actor
from linker_engine.planning.workspace import Workspace


def test_monthly_chart_integrates_the_verified_period_without_an_annual_guess() -> None:
    start = datetime(2020, 1, 1, tzinfo=UTC)
    middle = datetime(2020, 2, 1, 12, tzinfo=UTC)
    end = datetime(2021, 1, 1, tzinfo=UTC)
    data = calendar_totals([(start, middle, 2, 4), (middle, end, 1, 3)])
    assert data is not None and data["years"] == 1
    assert data["pv_kwh"] == [
        31 * 24 * 2,
        29 * 24 + 12,
        31 * 24,
        30 * 24,
        31 * 24,
        30 * 24,
        31 * 24,
        31 * 24,
        30 * 24,
        31 * 24,
        30 * 24,
        31 * 24,
    ]
    assert isinstance(data["load_kwh"], list) and data["load_kwh"][:2] == [
        31 * 24 * 4,
        29 * 24 * 3 + 12,
    ]
    assert calendar_totals([(start, middle, 2, None)]) is None
    assert calendar_totals([(start, middle, 0, 5), (middle, end, 0, 5)]) is None
    assert (
        calendar_totals(
            [(start, middle, 2, None), (datetime(2020, 2, 3, tzinfo=UTC), end, 1, None)]
        )
        is None
    )


@pytest.mark.parametrize("dc", [True, False])
def test_monthly_energy_uses_actual_generation_after_curtailment(dc: bool) -> None:
    from linker_engine.planning.canonical import Object

    frame: Object = {
        "interval": {
            "start_utc": "2020-01-01T00:00:00+00:00",
            "end_utc": "2021-01-01T00:00:00+00:00",
        },
        "load_kw": 2,
        "load_measurement": "critical_load",
    }
    flow: Object = {"frame": frame}
    if dc:
        frame["pv_available_dc_kw"] = 3
        flow.update(pv_available_dc_kw=3, pv_curtailed_dc_kw=1)
    else:
        flow.update(pv_available_kw=3, curtailed_kw=1)
    result = replay_months({"flows": [flow]})
    assert (
        result
        and isinstance(result["pv_kwh"], list)
        and result["pv_kwh"][0] == 31 * 24 * 2
    )
    assert result["load_kwh"] is None


def test_equipment_comparison_plots_both_frozen_profiles_in_their_calendar_months(
    workspace: Workspace, owner: Actor
) -> None:
    from datetime import timedelta
    from linker_engine.planning.assets import Assets
    from linker_engine.planning.canonical import Object
    from linker_engine.planning.profile_assets import profile_dependencies
    from linker_engine.planning.report_overview import comparison_months
    from linker_engine.planning.profile_import import ProfileImport
    from linker_engine.planning.power_series import Measurement
    from .test_energy_kernel import PROVENANCE, mapping

    project = workspace.create(owner, "Monthly chart", {}, key="monthly")
    pinned: Object = {}
    profiles: list[tuple[Measurement, int, int]] = [
        ("pv_available_ac", 0, 2),
        ("gross_load", 1, 4),
    ]
    for role, lead, watts in profiles:
        start = datetime(2020, 1, 1, tzinfo=UTC) - timedelta(hours=lead)
        data = "time,power\n" + "".join(
            f"{(start + timedelta(hours=h)).isoformat()},{watts}\n"
            for h in range(366 * 24)
        )
        item = ProfileImport(Assets(workspace)).csv(
            owner, project.id, data.encode(), mapping(role), PROVENANCE, key=role
        )
        pinned.update(profile_dependencies(item, role, {}, workspace.blobs))
    monthly = comparison_months(workspace.blobs, pinned, None)
    assert monthly is not None and monthly["load_timezone"] == "Europe/Berlin"
    assert isinstance(monthly["pv_kwh"], list) and monthly["pv_kwh"][2] == 31 * 24 * 2
    assert (
        isinstance(monthly["load_kwh"], list)
        and monthly["load_kwh"][2] == (31 * 24 - 1) * 4
    )
