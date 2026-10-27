"""Reject a PVGIS response for another place, array, loss, database or years."""

from __future__ import annotations

from .canonical import Json, Object
from .errors import InvalidInput
from .pvgis_request import PvgisRequest


def at(document: Object, *path: str) -> Json:
    value: Json = document
    for part in path:
        if not isinstance(value, dict) or part not in value:
            raise InvalidInput("PVGIS response field missing: " + ".".join(path))
        value = value[part]
    return value


def same(document: Object, path: tuple[str, ...], expected: Json) -> None:
    value = at(document, *path)
    # JSON integers/floats are both numbers; booleans are not numeric values.
    if type(expected) in (int, float):
        valid = type(value) in (int, float) and value == expected
    else:
        valid = type(value) is type(expected) and value == expected
    if not valid:
        raise InvalidInput("PVGIS response differs from request: " + ".".join(path))


def check_metadata(document: Object, request: PvgisRequest) -> None:
    inputs = at(document, "inputs")
    if not isinstance(inputs, dict):
        raise InvalidInput("PVGIS input metadata required")
    checks: list[tuple[tuple[str, ...], Json]] = [
        (("location", "latitude"), request.latitude_deg),
        (("location", "longitude"), request.longitude_deg),
        (("meteo_data", "radiation_db"), request.radiation_database),
        (("meteo_data", "meteo_db"), "ERA5"),
        (("meteo_data", "year_min"), request.start_year),
        (("meteo_data", "year_max"), request.end_year),
        (("meteo_data", "use_horizon"), request.use_terrain_horizon),
        (
            ("pv_module", "technology"),
            {
                "crystSi": "c-Si",
                "crystSi2025": "c-Si2025",
                "CIS": "CIS",
                "CdTe": "CdTe",
                "Unknown": "Unknown type",
            }[request.pv_technology],
        ),
        (("pv_module", "peak_power"), request.peak_power_kwp),
        (("pv_module", "system_loss"), request.system_loss_percent),
        (("mounting_system", "fixed", "slope", "value"), request.tilt_deg),
        (("mounting_system", "fixed", "slope", "optimal"), False),
        (
            ("mounting_system", "fixed", "azimuth", "value"),
            request.azimuth_north_clockwise_deg - 180,
        ),
        (("mounting_system", "fixed", "azimuth", "optimal"), False),
        (
            ("mounting_system", "fixed", "type"),
            "free-standing"
            if request.mounting_place == "free"
            else "building-integrated",
        ),
    ]
    for path, expected in checks:
        same(inputs, path, expected)
    if request.use_terrain_horizon:
        same(inputs, ("meteo_data", "horizon_data"), "DEM-calculated")
    mounting = at(inputs, "mounting_system")
    if not isinstance(mounting, dict) or set(mounting) != {"fixed"}:
        raise InvalidInput("only the requested fixed-plane system is supported")
    # These units are read rather than inferred from the magnitude of P.
    for path, unit in (
        (("outputs", "hourly", "variables", "P", "units"), "W"),
        (("inputs", "pv_module", "variables", "peak_power", "units"), "kW"),
        (("inputs", "pv_module", "variables", "system_loss", "units"), "%"),
    ):
        same(document, ("meta", *path), unit)
