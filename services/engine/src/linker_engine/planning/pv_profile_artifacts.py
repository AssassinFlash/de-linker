"""Read the producer's immutable PV output without rerunning numerical models."""

from __future__ import annotations

import math
from datetime import datetime

from .canonical import Json, Object, digest, encode
from .errors import InvalidInput, VersionUnavailable
from .interval import Interval
from .power_series import PowerSeries
from .pv_parameters import PvGenerationParameters
from .pv_profile_preparation import PROFILE_PURPOSE
from .pv_reconstruction import PvReconstruction
from .series_source import SeriesSource
from .storage import Blobs


def model_dependencies(metadata: Object) -> dict[str, str]:
    dependencies = metadata.get("dependencies")
    if not isinstance(dependencies, dict) or set(dependencies) != {
        "pv_model_inputs",
        "pv_model_witness",
    }:
        raise VersionUnavailable("PV model input and witness dependencies required")
    if any(not isinstance(value, str) for value in dependencies.values()):
        raise VersionUnavailable("PV model dependency hash required")
    return {name: str(value) for name, value in dependencies.items()}


def _object(value: Json) -> Object:
    if not isinstance(value, dict):
        raise VersionUnavailable("PV output document must be an object")
    return value


def _number(value: Json) -> float:
    try:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError
        result = float(value)
        if not math.isfinite(result):
            raise ValueError
        # Preserve the producer's integer/float representation in hashed policy.
        return value
    except (OverflowError, ValueError) as error:
        raise VersionUnavailable("finite PV output number required") from error


def _instant(value: Json) -> datetime:
    if not isinstance(value, str):
        raise VersionUnavailable("PV output interval timestamp required")
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise VersionUnavailable("invalid PV output interval timestamp") from error


def prepared_profile(blobs: Blobs, raw_sha256: str, metadata: Object) -> PowerSeries:
    """Project hash-verified output; full physical reproduction stays in workers.

    The trusted producer already retains every output value in its witness and
    the exact interval axis in its model inputs. No new copy of that year or
    current pvlib version is needed for a read. Cross-bind both artifacts and
    the original weather; malformed or mismatched stored artifacts fail closed.
    """
    if (
        type(metadata.get("schema")) is not int
        or metadata.get("schema") != 1
        or metadata.get("profile_type") != PROFILE_PURPOSE
        or metadata.get("retention") != "permanent"
        or metadata.get("timezone_rules_sha256") is not None
        or "csv_mapping" in metadata
    ):
        raise VersionUnavailable("unsupported pinned PV profile metadata")
    dependencies = model_dependencies(metadata)
    input_hash = dependencies["pv_model_inputs"]
    inputs = blobs.object(input_hash)
    witness = blobs.object(dependencies["pv_model_witness"])
    blobs.read(raw_sha256)
    parameters = PvGenerationParameters.read(inputs.get("parameters"))
    for document in (inputs, witness):
        if (
            type(document.get("schema_version")) is not int
            or document.get("schema_version") != 1
            or document.get("kind") != parameters.model
        ):
            raise VersionUnavailable("unsupported pinned PV output version")
    weather = _object(inputs.get("weather"))
    weather_source = _object(weather.get("source"))
    details = _object(witness.get("inputs"))
    if (
        type(weather.get("schema_version")) is not int
        or weather.get("schema_version") != 1
        or weather.get("kind") != "weather_with_explicit_irradiance_instants_v1"
        or weather_source.get("raw_sha256") != raw_sha256
        or metadata.get("geometry_sha256") != digest(encode(inputs.get("geometry")))
        or details.get("model") != parameters.model
        or details.get("input_bundle_sha256") != input_hash
        or details.get("geometry_sha256") != digest(encode(inputs.get("geometry")))
        or details.get("parameters_sha256") != digest(encode(inputs.get("parameters")))
        or details.get("weather_document_sha256") != digest(encode(weather))
        or details.get("weather_original_sha256") != raw_sha256
        or encode(details.get("weather_source")) != encode(weather_source)
    ):
        raise VersionUnavailable("PV output differs from its pinned input or source")
    points, values = weather.get("points"), witness.get("available_ac_w")
    if not isinstance(points, list) or not isinstance(values, list) or not points:
        raise VersionUnavailable("PV output requires its complete axis and values")
    try:
        intervals = tuple(
            Interval(
                _instant(_object(p).get("start_utc")),
                _instant(_object(p).get("end_utc")),
            )
            for p in points
        )
        axis: Object = {
            "intervals": [
                {"start_utc": item.start.isoformat(), "end_utc": item.end.isoformat()}
                for item in intervals
            ]
        }
        native = _number(weather_source.get("native_max_interval_seconds"))
        transformation = PvReconstruction(
            input_hash,
            digest(encode(axis)),
            native,
            max(p.hours * 3600 for p in intervals),
        )
        if encode(details.get("temporal_policy")) != encode(transformation.document()):
            raise VersionUnavailable(
                "PV output time policy differs from its pinned axis"
            )
        result = PowerSeries(
            intervals,
            # SI unit conversion, matching the producer: 1000 W per kW.
            tuple(_number(value) / 1000 for value in values),
            "pv_available_ac",
            SeriesSource(input_hash, "modelled", "UTC", native, encode(details)),
            (transformation,),
        )
        # Retained watts and energy are stored at the platform-stable
        # spelling, so the summed read-back matches the stored energy within
        # its documented 1e-9 relative quantum (2x margin below).
        if not math.isclose(
            result.total_kwh,
            _number(witness.get("energy_kwh")),
            rel_tol=2e-9,
            abs_tol=1e-12,
        ):
            raise VersionUnavailable("PV output energy differs from retained values")
        return result
    except InvalidInput as error:
        raise VersionUnavailable("invalid pinned PV output profile") from error
