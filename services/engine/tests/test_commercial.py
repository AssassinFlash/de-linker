"""C&I: a 15-minute load profile sizes peak shaving; without one, only indicative ranges."""

import pytest

from linker_engine import commercial
from linker_engine.engine import Engine
from linker_engine.models import CommercialInput

INTERVALS_PER_DAY = 96


def profile(days: int = 365) -> list[float]:
    """40 kW at night, 80 kW from 07:00 to 18:00, one 15-minute spike of 100 kW on day 100."""
    load = []
    for day in range(days):
        for interval in range(INTERVALS_PER_DAY):
            hour = interval / 4
            value = 80.0 if 7 <= hour < 18 else 40.0
            if day == 100 and interval == 48:
                value = 100.0
            load.append(value)
    return load


def csv_text(load: list[float], decimal: str = ".") -> str:
    lines = ["Zeitstempel;Leistung kW"]
    for index, value in enumerate(load):
        lines.append(f"{index};{str(value).replace('.', decimal)}")
    return "\n".join(lines)


def request(**fields: object) -> CommercialInput:
    values: dict[str, object] = {
        "plz": "80538",
        "grid_connection_kva": 135,
        "annual_kwh": 400000,
        "goals": ["peak_shaving"],
    }
    values.update(fields)
    return CommercialInput.model_validate(values)


def test_reading_german_csv_and_energy_per_interval() -> None:
    load = profile(10)
    assert commercial.parse_load_profile(csv_text(load, ","), "kW") == load
    energy = [v * 0.25 for v in load]
    assert commercial.parse_load_profile(csv_text(energy), "kWh") == pytest.approx(load)
    with pytest.raises(commercial.LoadProfileError):
        commercial.parse_load_profile("1;2\n3;4", "kW")


def test_peak_shaving_from_the_profile(engine: Engine) -> None:
    result = commercial.design(
        engine, request(load_profile_csv=csv_text(profile()), target_peak_kw=90), "now"
    )
    assert result.status == "sized"
    assert result.load is not None and result.load.peak_kw == 100
    # 10 kW above the cap for one interval: 2.5 kWh at the AC side, through 94 % discharge efficiency.
    assert result.power_kw_range is not None and result.power_kw_range.low == 10
    assert result.energy_kwh_range is not None
    assert result.energy_kwh_range.low == pytest.approx(2.5 / 0.94, abs=0.05)
    assert not any("recharge" in w.lower() for w in result.warnings)


def test_a_cap_below_the_daytime_load_cannot_recharge(engine: Engine) -> None:
    result = commercial.design(
        engine, request(load_profile_csv=csv_text(profile()), target_peak_kw=60), "now"
    )
    # 20 kW above 60 for 11 hours a day and only 20 kW of room for 13 hours: tight but possible;
    # at 45 kW the daily need exceeds the room below the cap.
    tight = commercial.design(
        engine, request(load_profile_csv=csv_text(profile()), target_peak_kw=45), "now"
    )
    assert result.power_kw_range is not None and result.power_kw_range.low == 40
    assert any(str(365) in w or "365" in w for w in tight.warnings)


def test_options_without_a_cap(engine: Engine) -> None:
    result = commercial.design(
        engine, request(load_profile_csv=csv_text(profile())), "now"
    )
    assert result.status == "indicative"
    assert [round(o.cap_kw) for o in result.options] == [95, 90, 85, 80, 75, 70]
    assert result.power_kw_range is None


def test_without_a_profile_only_indicative_ranges_and_an_inquiry(
    engine: Engine,
) -> None:
    result = commercial.design(
        engine,
        request(
            goals=["peak_shaving", "self_consumption"],
            peak_kw=200,
            target_peak_kw=150,
            pv_kwp=100,
        ),
        "now",
    )
    assert result.status == "indicative"
    assert result.energy_kwh_range is not None
    # Peak: 50 kW for one to two hours; self-consumption: 1 kWh per kWp for 100 kWp.
    assert (result.energy_kwh_range.low, result.energy_kwh_range.high) == (150.0, 200.0)
    assert result.inquiry.startswith("mailto:sales@de-linker.com")
    assert any("100.000" in w or "100,000" in w for w in result.warnings)


def test_grid_code_notes(engine: Engine) -> None:
    result = commercial.design(
        engine, request(grid_connection_kva=200, goals=["self_consumption"]), "now"
    )
    assert any("4110" in w for w in result.warnings)
    assert any("NA" in w for w in result.warnings)
