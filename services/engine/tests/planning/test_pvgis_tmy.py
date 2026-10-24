"""Actual JRC typical-weather bytes and independently checked two-axis mapping."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest

from linker_engine.planning.canonical import Object, decode_object, encode
from linker_engine.planning.errors import InvalidInput
from linker_engine.planning.pv_generation import generate_pv
from linker_engine.planning.pv_weather import WeatherSeries
from linker_engine.planning.pvgis_response import PvgisCapture
from linker_engine.planning.pvgis_tmy import tmy_weather
from linker_engine.planning.pvgis_tmy_request import (
    PvgisTmyInterpretation,
    PvgisTmyRequest,
)

from .test_pv_generation import geometry, parameter_document

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "docs/research/2026-10-24-pv-generation/raw"


def raw() -> bytes:
    return (RAW / "berlin-2005-2023-nohorizon.tmy.json").read_bytes()


def request() -> PvgisTmyRequest:
    return PvgisTmyRequest(
        schema_version=1,
        api_version="5.3",
        latitude_deg=52.52,
        longitude_deg=13.405,
        start_year=2005,
        end_year=2023,
        use_terrain_horizon=False,
        radiation_database_policy="provider_default_with_verified_echo",
        expected_radiation_database="PVGIS-SARAH3",
        expected_meteo_database="ERA5",
    )


def capture() -> PvgisCapture:
    record = json.loads((RAW / "weather-provenance.json").read_bytes())
    return PvgisCapture(
        schema_version=1,
        requested_url=record["providerURL"],
        loaded_url=record["loadedURL"],
        status=record["httpStatus"],
        content_type=record["contentType"],
        received_at_utc=record["loadedTime"],
        capture_basis=record["capture"],
        source_identifiers={
            "apify_run": record["apifyRun"],
            "apify_record": record["apifyRecord"],
        },
    )


def interpretation() -> PvgisTmyInterpretation:
    return PvgisTmyInterpretation(
        schema_version=1,
        synthetic_energy_year=2023,
        solar_date_policy="original_selected_year_plus_reported_irradiance_offset",
        output_axis_policy="nonleap_synthetic_utc_hourly_scenario_v1",
        power_reconstruction="representative_pv_output_over_declared_intervals_v1",
    )


def parse(content: bytes | None = None) -> WeatherSeries:
    return tmy_weather(
        raw() if content is None else content,
        request(),
        capture(),
        interpretation(),
        max_bytes=2_000_000,
        max_rows=9000,
    )


def test_exact_original_preserves_native_month_years_offset_and_distinct_energy_axis() -> (
    None
):
    weather = parse()
    assert (
        weather.source.raw_sha256
        == "5406a027f131e780d2a7a79a98d1f79b9e62c6ab7fe4b2f212a1829553321110"
    )
    assert len(weather.points) == 8760 and weather.source.origin == "template"
    first, last = weather.points[0], weather.points[-1]
    assert first.source_label_utc == datetime(2021, 1, 1, tzinfo=UTC)
    assert first.irradiance_at_utc == datetime(2021, 1, 1, 0, 11, 1, 680000, tzinfo=UTC)
    assert last.source_label_utc == datetime(2014, 12, 31, 23, tzinfo=UTC)
    assert first.interval.start == datetime(2023, 1, 1, tzinfo=UTC)
    assert last.interval.end == datetime(2024, 1, 1, tzinfo=UTC)
    assert sum(p.interval.hours for p in weather.points) == 8760
    assert any(
        a.source_label_utc > b.source_label_utc
        for a, b in zip(weather.points, weather.points[1:], strict=False)
    )
    assert all(
        b.interval.start == a.interval.end
        for a, b in zip(weather.points, weather.points[1:], strict=False)
    )
    assert all(
        p.irradiance_at_utc - p.source_label_utc == timedelta(seconds=661.68)
        for p in weather.points
    )
    assert (
        min(p.air_temp_2m_c for p in weather.points),
        max(p.air_temp_2m_c for p in weather.points),
    ) == (-14.87, 36)
    assert first.pressure_pa == 100020 and first.wind_10m_m_s == 2.24
    details = decode_object(weather.source.details_json)
    assert len(cast(list[Object], details["months_selected"])) == 12
    assert details["irradiance_offset_microseconds"] == 661680000
    assert details["ac_interval_energy_preservation_claim"] is False


def test_actual_tmy_executes_the_entire_explicit_pv_chain_without_live_reads() -> None:
    from linker_engine.planning.pv_parameters import PvGenerationParameters

    data = parameter_document()
    data["arrays"][0]["thermal"].update(a=-3.47, b=-0.0594, delta_t_c=3)
    data["arrays"][0]["transposition"] = "perez"
    geo = geometry()
    geo["arrays"][0]["mount_tilt_deg"] = 30
    weather = parse()
    result = generate_pv(
        geo, weather, PvGenerationParameters.read(data), max_array_steps=9000
    )
    assert len(result.profile.values_kw) == 8760
    assert all(
        math.isfinite(value) and value >= 0 for value in result.profile.values_kw
    )
    assert result.profile.total_kwh > 0
    witness = result.witness()
    arrays = cast(list[Object], witness["arrays"])
    assert arrays[0]["module_count"] == 5 and arrays[0]["stc_power_w"] == 2500
    assert arrays[0]["tilt_deg"] == pytest.approx(30, rel=0, abs=1e-12)
    assert witness["near_shading_assessment"] == {
        "status": "not_assessed",
        "policy": "explicit_unshaded_reference",
    }
    assert (
        witness["equipment_release"]
        == witness["country_assessment"]
        == {"status": "not_assessed"}
    )
    profile = result.profile.document()
    assert profile["reconstructed_means"] is True
    assert profile["effective_max_interval_seconds"] == 3600
    assert result.profile.total_kwh == pytest.approx(
        math.fsum(result.profile.values_kw), rel=0, abs=1e-9
    )


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["inputs"]["location"].update(latitude=52.53),
        lambda d: d["meta"]["inputs"]["location"]["variables"]["elevation"].update(
            units="km"
        ),
        lambda d: d["inputs"]["location"].pop("irradiance_time_offset"),
        lambda d: d["inputs"]["meteo_data"].update(radiation_db="PVGIS-ERA5"),
        lambda d: d["inputs"]["meteo_data"].update(year_min=2006),
        lambda d: d["inputs"]["meteo_data"].update(use_horizon=True),
        lambda d: d["outputs"]["months_selected"][0].update(year=2019),
        lambda d: d["outputs"]["months_selected"].pop(),
        lambda d: d["outputs"]["tmy_hourly"].pop(),
        lambda d: d["outputs"]["tmy_hourly"][1].update({"time(UTC)": "20210101:0000"}),
        lambda d: d["outputs"]["tmy_hourly"][0].update({"G(h)": -1}),
        lambda d: d["outputs"]["tmy_hourly"][0].update({"Gb(n)": True}),
        lambda d: d["outputs"]["tmy_hourly"][0].update({"T2m": None}),
        lambda d: d["meta"]["outputs"]["tmy_hourly"]["variables"]["SP"].update(
            units="kPa"
        ),
        lambda d: d["meta"]["outputs"]["tmy_hourly"]["variables"]["WS10m"].update(
            description="2-m wind"
        ),
    ],
)
def test_actual_format_requires_complete_identity_units_and_time_axis(
    change: Any,
) -> None:
    document = json.loads(raw())
    change(document)
    with pytest.raises(InvalidInput):
        parse(json.dumps(document).encode())


def test_duplicate_nonfinite_and_all_zero_meteorology_are_not_repaired() -> None:
    with pytest.raises(InvalidInput):
        parse(b'{"inputs":null,' + raw()[1:])
    with pytest.raises(InvalidInput):
        parse(raw().replace(b'"T2m":1.76', b'"T2m":NaN', 1))
    document = json.loads(raw())
    for row in document["outputs"]["tmy_hourly"]:
        row.update(T2m=0, WS10m=0)
    with pytest.raises(InvalidInput, match="source verification"):
        parse(encode(document))


def test_request_capture_and_calendar_cannot_silently_change() -> None:
    req = request()
    assert req.matches_url(capture().requested_url) and req.matches_url(req.url)
    for value in (
        req.url + "&raddatabase=PVGIS-ERA5",
        req.url + "&lat=52.52",
        req.url.replace("v5_3", "v5_2"),
        req.url.replace("re.jrc.ec.europa.eu", "example.test"),
    ):
        assert not req.matches_url(value)
    for cap in (
        capture().model_copy(update={"status": 429}),
        capture().model_copy(update={"content_type": "text/html"}),
        capture().model_copy(update={"loaded_url": "https://example.test/body"}),
    ):
        with pytest.raises(InvalidInput):
            tmy_weather(
                raw(), req, cap, interpretation(), max_bytes=2_000_000, max_rows=9000
            )
    with pytest.raises(InvalidInput, match="non-leap"):
        tmy_weather(
            raw(),
            req,
            capture(),
            interpretation().model_copy(update={"synthetic_energy_year": 2024}),
            max_bytes=2_000_000,
            max_rows=9000,
        )
    for limits in (
        {"max_bytes": 100, "max_rows": 9000},
        {"max_bytes": 2_000_000, "max_rows": 8759},
    ):
        with pytest.raises(InvalidInput):
            tmy_weather(raw(), req, capture(), interpretation(), **limits)
