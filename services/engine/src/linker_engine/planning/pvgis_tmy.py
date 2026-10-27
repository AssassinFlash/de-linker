"""Frozen typical weather, preserving source dates and a separate scenario axis."""

from __future__ import annotations

import calendar
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast

from .access import positive_integer
from .canonical import Json, Object, digest, encode
from .errors import InvalidInput
from .interval import Interval
from .pv_weather import WeatherPoint, WeatherSeries
from .pvgis_document import number, read_object
from .pvgis_metadata import at
from .pvgis_response import PvgisCapture
from .pvgis_tmy_request import PvgisTmyInterpretation, PvgisTmyRequest
from .series_source import SeriesSource
from .weather_fetch_errors import SourceQualityField, WeatherSourceQualityInvalid


def tmy_weather(
    content: bytes,
    request: PvgisTmyRequest,
    capture: PvgisCapture,
    interpretation: PvgisTmyInterpretation,
    *,
    max_bytes: int,
    max_rows: int,
) -> WeatherSeries:
    positive_integer(max_bytes, "TMY byte limit")
    positive_integer(max_rows, "TMY row limit")
    if not content or len(content) > max_bytes:
        raise InvalidInput("TMY response is empty or exceeds resource limits")
    if (
        capture.status != 200
        or capture.content_type.split(";", 1)[0].strip().lower() != "application/json"
        or not request.matches_url(capture.requested_url)
        or not request.matches_url(capture.loaded_url)
    ):
        raise InvalidInput("TMY capture is not the requested official JSON response")
    year = interpretation.synthetic_energy_year
    if calendar.isleap(year):
        raise InvalidInput(
            "TMY scenario axis requires an explicit non-leap year; no leap day is invented"
        )
    document = read_object(content)
    location = at(document, "inputs", "location")
    meteo = at(document, "inputs", "meteo_data")
    if not isinstance(location, dict) or not isinstance(meteo, dict):
        raise InvalidInput("TMY location and meteorology echoes required")
    for field, unit in {
        "latitude": "decimal degree",
        "longitude": "decimal degree",
        "elevation": "m",
    }.items():
        if (
            at(document, "meta", "inputs", "location", "variables", field, "units")
            != unit
        ):
            raise InvalidInput("TMY location unit mismatch: " + field)
    if (
        (number(location, "latitude"), number(location, "longitude"))
        != (
            request.latitude_deg,
            request.longitude_deg,
        )
        or meteo.get("radiation_db") != request.expected_radiation_database
        or meteo.get("meteo_db") != request.expected_meteo_database
    ):
        raise InvalidInput("TMY location or database differs from explicit expectation")
    if (
        type(meteo.get("year_min")) is not int
        or type(meteo.get("year_max")) is not int
        or meteo["year_min"] != request.start_year
        or meteo["year_max"] != request.end_year
        or meteo.get("use_horizon") is not request.use_terrain_horizon
    ):
        raise InvalidInput("TMY selection years or horizon differ from request")
    for field, unit in {
        "T2m": "degree Celsius",
        "G(h)": "W/m2",
        "Gb(n)": "W/m2",
        "Gd(h)": "W/m2",
        "WS10m": "m/s",
        "SP": "Pa",
    }.items():
        if (
            at(document, "meta", "outputs", "tmy_hourly", "variables", field, "units")
            != unit
        ):
            raise InvalidInput("TMY weather unit mismatch: " + field)
    for field, description in {
        "T2m": "2-m air temperature",
        "WS10m": "10-m total wind speed",
    }.items():
        if (
            at(
                document,
                "meta",
                "outputs",
                "tmy_hourly",
                "variables",
                field,
                "description",
            )
            != description
        ):
            raise InvalidInput(
                "TMY meteorological measurement height differs: " + field
            )
    selected = at(document, "outputs", "months_selected")
    if not isinstance(selected, list) or len(selected) != 12:
        raise InvalidInput("TMY requires all twelve selected month-years")
    selected_years: list[int] = []
    for month, item in enumerate(selected, start=1):
        if (
            not isinstance(item, dict)
            or type(item.get("month")) is not int
            or item["month"] != month
            or type(item.get("year")) is not int
            or not request.start_year <= cast(int, item["year"]) <= request.end_year
        ):
            raise InvalidInput("TMY selected month-year identity is invalid")
        selected_years.append(cast(int, item["year"]))
    offset = number(location, "irradiance_time_offset")
    micros = Decimal(str(offset)) * Decimal(3_600_000_000)
    if micros != micros.to_integral_value():
        raise InvalidInput("TMY irradiance offset exceeds timestamp representation")
    rows = at(document, "outputs", "tmy_hourly")
    start, end = datetime(year, 1, 1, tzinfo=UTC), datetime(year + 1, 1, 1, tzinfo=UTC)
    count = (end - start).days * 24
    if not isinstance(rows, list) or len(rows) != count or len(rows) > max_rows:
        raise InvalidInput("complete TMY hourly axis required within resource limits")
    points = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise InvalidInput("TMY hourly row must be an object")
        target = start + timedelta(hours=index)
        source = target.replace(year=selected_years[target.month - 1])
        if row.get("time(UTC)") != source.strftime("%Y%m%d:%H%M"):
            raise InvalidInput(
                "TMY source hours or selected years are missing, duplicated or out of order"
            )
        try:
            sample = source + timedelta(microseconds=int(micros))
        except OverflowError as error:
            raise InvalidInput(
                "TMY irradiance instant cannot be represented"
            ) from error
        values = {
            field: number(row, field)
            for field in ("G(h)", "Gb(n)", "Gd(h)", "T2m", "WS10m", "SP")
        }
        for field in ("G(h)", "Gb(n)", "Gd(h)", "WS10m"):
            if values[field] < 0:
                raise WeatherSourceQualityInvalid(
                    "negative_wind" if field == "WS10m" else "negative_irradiance",
                    cast(SourceQualityField, field),
                    index,
                    source.isoformat(),
                    values[field],
                )
        points.append(
            WeatherPoint(
                Interval(target, target + timedelta(hours=1)),
                source,
                sample,
                values["G(h)"],
                values["Gb(n)"],
                values["Gd(h)"],
                values["T2m"],
                values["WS10m"],
                values["SP"],
            )
        )
    # Observed provider failure elsewhere returned zero meteorology, not
    # missing-value markers. Do not silently admit the same unresolved shape.
    if all(p.air_temp_2m_c == 0 and p.wind_10m_m_s == 0 for p in points):
        raise InvalidInput("all-zero TMY meteorology needs source verification")
    month_records: list[Json] = [item for item in selected]
    details: Object = {
        "adapter": "pvgis_5_3_tmy_explicit_two_axes_v1",
        "request": {**request.model_dump(mode="json")},
        "capture": capture.document(),
        "interpretation": {**interpretation.model_dump(mode="json")},
        "provider_inputs": document["inputs"],
        "provider_metadata": document["meta"],
        "months_selected": month_records,
        "irradiance_time_offset_hours": offset,
        "irradiance_offset_microseconds": int(micros),
        "weather_kind": "stitched_typical_months_not_observed_historical_year",
        "solar_date_basis": interpretation.solar_date_policy,
        "energy_axis_basis": interpretation.output_axis_policy,
        "meteorology_time_basis": "provider_hourly_conditions_no_new_subhourly_observations",
        "native_radiation_semantics": "sarah_instantaneous"
        if request.expected_radiation_database == "PVGIS-SARAH3"
        else "era5_hourly_mean",
        "radiation_database": request.expected_radiation_database,
        "meteo_database": request.expected_meteo_database,
        "ac_interval_energy_preservation_claim": False,
    }
    return WeatherSeries(
        request.latitude_deg,
        request.longitude_deg,
        number(location, "elevation"),
        tuple(points),
        SeriesSource(digest(content), "template", "UTC", 3600, encode(details)),
    )
