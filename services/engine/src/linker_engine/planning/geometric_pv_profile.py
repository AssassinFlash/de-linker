"""Owned immutable geometric-reference profiles; reads do not run physics."""

from __future__ import annotations

from typing import cast

from .assets import Asset
from .canonical import Object, digest, encode
from .errors import InvalidInput, VersionUnavailable
from .frozen_documents import FrozenDocuments
from .geometric_pv_inputs import MODEL, PROFILE_PURPOSE, GeometricPvInputs
from .interval import Interval
from .power_series import PowerSeries
from .product_sources import ProductSources
from .pv_profile_artifacts import _instant, _number, _object
from .pv_reconstruction import PvReconstruction
from .series_source import SeriesSource
from .storage import Blobs

DEPENDENCIES = {
    "model.inputs",
    "model.witness",
    "project.parameters",
    "weather.raw",
    "weather.metadata",
    "woo.module_inputs",
}


def reference_bundle(
    blobs: Blobs,
    raw_sha256: str,
    metadata: Object,
    documents: FrozenDocuments | None = None,
) -> Object:
    """Verify the manifest, then read its artifacts through one bounded reader.

    `documents` lets the callers of a single report share the parsed witness
    instead of re-reading it per section. Without one, this call is the reader,
    so a standalone read keeps its original behaviour.
    """
    documents = FrozenDocuments(blobs) if documents is None else documents
    if (
        type(metadata.get("schema")) is not int
        or metadata.get("schema") != 1
        or metadata.get("profile_type") != PROFILE_PURPOSE
        or metadata.get("retention") != "permanent"
        or metadata.get("timezone_rules_sha256") is not None
        or "csv_mapping" in metadata
    ):
        raise VersionUnavailable("unsupported geometric PV reference metadata")
    manifest = documents.object(raw_sha256)
    dependencies = _object(metadata.get("dependencies"))
    if (
        manifest.get("schema_version") != 1
        or manifest.get("kind") != MODEL
        or manifest.get("dependencies") != dependencies
        or set(dependencies) != DEPENDENCIES
        or any(not isinstance(sha, str) for sha in dependencies.values())
    ):
        raise VersionUnavailable("geometric PV dependency manifest differs")
    for sha in dependencies.values():
        documents.read(str(sha))
    inputs = documents.object(str(dependencies["model.inputs"]))
    witness = documents.object(str(dependencies["model.witness"]))
    original_parameters = documents.object(str(dependencies["project.parameters"]))
    parameters = GeometricPvInputs.read(original_parameters)
    weather = _object(inputs.get("weather"))
    source = _object(weather.get("source"))
    details = _object(witness.get("inputs"))
    basis = documents.object(str(dependencies["woo.module_inputs"]))
    weather_metadata = documents.object(str(dependencies["weather.metadata"]))
    if (
        any(
            document.get("schema_version") != 1 or document.get("kind") != MODEL
            for document in (inputs, witness)
        )
        or inputs.get("parameters") != parameters.model_dump(mode="json")
        or metadata.get("parameters_sha256") != dependencies["project.parameters"]
        or metadata.get("geometry_sha256") != digest(encode(inputs.get("geometry")))
        or metadata.get("woo_module_inputs") != basis
        or details.get("model") != MODEL
        or details.get("input_bundle_sha256") != dependencies["model.inputs"]
        or details.get("geometry_sha256") != metadata["geometry_sha256"]
        or details.get("parameters_sha256") != digest(encode(inputs.get("parameters")))
        or details.get("weather_document_sha256") != digest(encode(weather))
        or details.get("weather_original_sha256") != dependencies["weather.raw"]
        or source.get("raw_sha256") != dependencies["weather.raw"]
        or details.get("weather_source") != source
        or details.get("limits") != inputs.get("limits")
    ):
        raise VersionUnavailable("geometric PV output differs from frozen sources")
    source_details = _object(source.get("details"))
    for name in ("request", "capture", "interpretation"):
        if source_details.get(name) != weather_metadata.get("weather_" + name):
            raise VersionUnavailable("geometric PV weather provenance differs")
    ProductSources.check_pv_inputs(
        {
            "geometry": inputs.get("geometry"),
            "pv_generation": parameters.parameters.model_dump(mode="json"),
        },
        basis,
    )
    return {
        "manifest": manifest,
        "inputs": inputs,
        "witness": witness,
        "weather_metadata": weather_metadata,
        "woo_module_inputs": basis,
        "dependencies": dependencies,
    }


def prepared_profile(
    blobs: Blobs,
    raw_sha256: str,
    metadata: Object,
    documents: FrozenDocuments | None = None,
    *,
    bundle: Object | None = None,
) -> PowerSeries:
    verified = (
        reference_bundle(blobs, raw_sha256, metadata, documents)
        if bundle is None
        else bundle
    )
    inputs, witness = _object(verified["inputs"]), _object(verified["witness"])
    weather = _object(inputs["weather"])
    points = weather.get("points")
    values = witness.get("available_ac_w")
    if not isinstance(points, list) or not points or not isinstance(values, list):
        raise VersionUnavailable("geometric PV complete axis and powers required")
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
        source = _object(weather["source"])
        native = _number(source.get("native_max_interval_seconds"))
        transform = PvReconstruction(
            str(_object(verified["dependencies"])["model.inputs"]),
            digest(encode(axis)),
            native,
            max(p.hours * 3600 for p in intervals),
        )
        details = _object(witness["inputs"])
        if details.get("temporal_policy") != transform.document():
            raise VersionUnavailable("geometric PV time policy differs")
        result = PowerSeries(
            intervals,
            tuple(_number(value) / 1000 for value in values),
            "pv_available_ac",
            SeriesSource(
                str(_object(verified["dependencies"])["model.inputs"]),
                "modelled",
                "UTC",
                native,
                encode(details),
            ),
            (transform,),
        )
        if result.total_kwh != _number(witness.get("energy_kwh")):
            raise VersionUnavailable("geometric PV energy differs from saved powers")
        expected_summary: Object = {
            "start_utc": intervals[0].start.isoformat(),
            "end_utc": intervals[-1].end.isoformat(),
            "interval_count": len(intervals),
            "energy_kwh": result.total_kwh,
            "measurement": "pv_available_ac",
            "origin": "modelled",
            "native_max_interval_seconds": native,
            "reconstructed_means": True,
            "model_role": "direct_only_geometry_uniform_module_reference_scenario",
        }
        if metadata.get("interpretation") != expected_summary or metadata.get(
            "weather"
        ) != {
            "interval_count": len(intervals),
            "start_utc": intervals[0].start.isoformat(),
            "end_utc": intervals[-1].end.isoformat(),
            "weather_document_sha256": digest(encode(weather)),
        }:
            raise VersionUnavailable(
                "geometric PV summary differs from complete source axis"
            )
        return result
    except InvalidInput as error:
        raise VersionUnavailable(
            "invalid retained geometric PV axis or powers"
        ) from error


def reference_dependencies(
    asset: Asset, inputs: Object, blobs: Blobs
) -> dict[str, str]:
    if (
        asset.purpose != PROFILE_PURPOSE
        or asset.metadata.get("geometry_sha256")
        != digest(encode(inputs.get("geometry")))
        or asset.metadata.get("parameters_sha256")
        != digest(encode(inputs.get("geometric_pv_preparation")))
    ):
        raise InvalidInput(
            "geometric PV profile differs from saved geometry or parameters"
        )
    bundle = reference_bundle(blobs, asset.content_sha256, asset.metadata)
    return {
        key: cast(str, value) for key, value in _object(bundle["dependencies"]).items()
    }
