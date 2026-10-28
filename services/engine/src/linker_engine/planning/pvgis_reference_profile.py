"""Read a frozen AC reference without HTTP or rerunning a provider/PV model."""

from datetime import UTC, datetime, timedelta
from typing import cast

from .assets import Asset
from .canonical import Json, Object, digest, encode
from .dependencies import verify_dependencies
from .errors import InvalidInput, VersionUnavailable
from .frozen_documents import FrozenReader
from .interval import Interval
from .power_series import PowerSeries
from .product_sources import ProductSources
from .pvgis_reference_artifacts import PROFILE_PURPOSE as PROFILE_PURPOSE
from .pvgis_reference_geometry import reference_plan
from .pvgis_reference_plan import PvgisReferencePlan
from .pvgis_response import PvgisCapture
from .sample_reconstruction import SampleReconstruction
from .series_source import SeriesSource
from .storage import Blobs


def obj(value: Json | None) -> Object:
    if not isinstance(value, dict):
        raise VersionUnavailable("roof reference requires its frozen object")
    return value


def reference_bundle(
    blobs: Blobs,
    raw_sha256: str,
    metadata: Object,
    documents: FrozenReader | None = None,
) -> Object:
    # A caller that already read this asset for another consumer of the same
    # report passes its reader, so the manifest and every child are verified
    # once per request instead of once per section.
    reader: FrozenReader = blobs if documents is None else documents
    if (
        metadata.get("schema") != 1
        or type(metadata.get("schema")) is not int
        or metadata.get("profile_type") != PROFILE_PURPOSE
        or metadata.get("retention") != "permanent"
        or "csv_mapping" in metadata
        or metadata.get("timezone_rules_sha256") is not None
    ):
        raise VersionUnavailable("unsupported roof AC reference profile")
    manifest = reader.object(raw_sha256)
    dependencies = obj(metadata.get("dependencies"))
    arrays = manifest.get("arrays")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("kind") != "pvgis_5_3_roof_ac_reference_v1"
        or not isinstance(arrays, list)
    ):
        raise VersionUnavailable("roof reference original manifest is invalid")
    expected: Object = {
        "reference_plan": manifest.get("plan_sha256"),
        "reference_geometry": manifest.get("geometry_sha256"),
        "reference_parameters": manifest.get("parameters_sha256"),
        "reference_woo_module": manifest.get("module_basis_sha256"),
        "reference_output": manifest.get("output_sha256"),
    }
    for index, item in enumerate(arrays):
        row = obj(item)
        expected[f"array.{index}.original"] = row.get("original_sha256")
        expected[f"array.{index}.capture"] = row.get("capture_sha256")
    if dependencies != expected or any(
        not isinstance(v, str) for v in dependencies.values()
    ):
        raise VersionUnavailable("roof reference dependencies differ from originals")
    verify_dependencies(reader, metadata)
    plan = PvgisReferencePlan.read(reader.object(str(dependencies["reference_plan"])))
    geometry = reader.object(str(dependencies["reference_geometry"]))
    parameters = reader.object(str(dependencies["reference_parameters"]))
    basis = reader.object(str(dependencies["reference_woo_module"]))
    try:
        ProductSources.check_roof_inputs({"geometry": geometry}, basis)
        regenerated = reference_plan(
            {"geometry": geometry, "pvgis_reference": parameters},
            str(dependencies["reference_woo_module"]),
            plan.limits,
            plan.max_array_steps,
        )
    except InvalidInput as error:
        raise VersionUnavailable(
            "roof reference geometry or product proof changed"
        ) from error
    if (
        encode(regenerated.document()) != encode(plan.document())
        or metadata.get("geometry_sha256") != plan.geometry_sha256
        or metadata.get("parameters_sha256") != plan.parameters_sha256
        or metadata.get("woo_module_inputs") != basis
        or len(arrays) != len(plan.arrays)
    ):
        raise VersionUnavailable("roof reference input/proof binding changed")
    for index, (raw, array) in enumerate(zip(arrays, plan.arrays, strict=True)):
        row = obj(raw)
        base = {
            key: value for key, value in row.items() if key in type(array).model_fields
        }
        capture = PvgisCapture.read(
            reader.object(str(dependencies[f"array.{index}.capture"]))
        )
        source = obj(row.get("source_document"))
        semantics = (
            "centered_hourly_mean"
            if plan.parameters.radiation_database == "PVGIS-ERA5"
            else "instantaneous_sample"
        )
        if (
            base != array.model_dump(mode="json")
            or not array.request.matches_url(capture.requested_url)
            or not array.request.matches_url(capture.loaded_url)
            or capture.status != 200
            or capture.capture_basis != "official_jrc_https_get_original_v1"
            or capture.source_identifiers
            != {"provider": "EC_JRC_PVGIS", "api_version": "5.3"}
            or row.get("native_value_semantics") != semantics
            or row.get("interpretation") != plan.parameters.interpretation().document()
            or source.get("request") != array.request.document()
            or source.get("capture") != capture.document()
            or source.get("raw_sha256") != row.get("original_sha256")
            or source.get("native_value_semantics") != semantics
        ):
            raise VersionUnavailable("roof reference array/capture binding changed")
    output = reader.object(str(dependencies["reference_output"]))
    if (
        output.get("schema_version") != 1
        or output.get("kind") != "pvgis_5_3_roof_ac_reference_output_v1"
        or output.get("plan_sha256") != manifest["plan_sha256"]
    ):
        raise VersionUnavailable("roof reference output binding changed")
    return {
        "manifest": manifest,
        "plan": plan.document(),
        "geometry": geometry,
        "parameters": parameters,
        "woo_module_inputs": basis,
        "output": output,
    }


def prepared_reference_profile(
    blobs: Blobs,
    raw_sha256: str,
    metadata: Object,
    documents: FrozenReader | None = None,
) -> PowerSeries:
    bundle = reference_bundle(blobs, raw_sha256, metadata, documents)
    manifest, output = obj(bundle["manifest"]), obj(bundle["output"])
    plan = PvgisReferencePlan.read(bundle["plan"])
    start = datetime(plan.parameters.year, 1, 1, tzinfo=UTC)
    end = datetime(plan.parameters.year + 1, 1, 1, tzinfo=UTC)
    intervals = tuple(
        Interval(start + timedelta(hours=i), start + timedelta(hours=i + 1))
        for i in range((end - start).days * 24)
    )
    axis: list[Json] = [
        {"start_utc": i.start.isoformat(), "end_utc": i.end.isoformat()}
        for i in intervals
    ]
    values = output.get("available_ac_kw")
    if output.get("intervals") != axis or not isinstance(values, list):
        raise VersionUnavailable("roof reference complete calendar-year axis changed")
    transformations = tuple(
        SampleReconstruction(
            digest(encode(obj(row).get("source_document"))), digest(encode(axis))
        )
        for row in cast(list[Json], manifest["arrays"])
        if plan.parameters.radiation_database == "PVGIS-SARAH3"
    )
    if output.get("transformations") != [t.document() for t in transformations]:
        raise VersionUnavailable("roof reference temporal interpretation changed")
    try:
        profile = PowerSeries(
            intervals,
            tuple(cast(float, value) for value in values),
            "pv_available_ac",
            SeriesSource(
                raw_sha256,
                "modelled",
                "UTC",
                3600,
                encode(
                    {
                        "adapter": "pvgis_5_3_roof_ac_reference_v1",
                        "model_role": "official_calendar_year_roof_ac_reference",
                        "plan_sha256": manifest["plan_sha256"],
                        "parameters": plan.parameters.model_dump(mode="json"),
                        "arrays": manifest["arrays"],
                        "geometry_sha256": plan.geometry_sha256,
                        "output_boundary": "provider_modelled_system_output_including_system_loss",
                        "not_modelled": [
                            "specific_module_and_inverter_electrical_release",
                            "shared_inverter_and_hybrid_port_constraints",
                            "near_field_and_inter_row_shading",
                            "country_and_grid_qualification",
                        ],
                    }
                ),
            ),
            transformations,
        )
    except InvalidInput as error:
        raise VersionUnavailable("invalid retained roof reference powers") from error
    summary: Object = {
        "start_utc": start.isoformat(),
        "end_utc": end.isoformat(),
        "interval_count": len(intervals),
        "energy_kwh": profile.total_kwh,
        "measurement": "pv_available_ac",
        "origin": "modelled",
        "native_max_interval_seconds": 3600,
        "reconstructed_means": profile.reconstructed_means,
        "model_role": "official_calendar_year_roof_ac_reference",
    }
    if (
        output.get("energy_kwh") != profile.total_kwh
        or metadata.get("interpretation") != summary
    ):
        raise VersionUnavailable("roof reference output summary changed")
    return profile


def reference_dependencies(
    asset: Asset, inputs: Object, blobs: Blobs
) -> dict[str, str]:
    if (
        asset.purpose != PROFILE_PURPOSE
        or asset.metadata.get("geometry_sha256")
        != digest(encode(inputs.get("geometry")))
        or asset.metadata.get("parameters_sha256")
        != digest(encode(inputs.get("pvgis_reference")))
    ):
        raise InvalidInput(
            "PVGIS roof reference differs from the saved roof or model choices"
        )
    reference_bundle(blobs, asset.content_sha256, asset.metadata)
    return {
        key: str(value)
        for key, value in obj(asset.metadata.get("dependencies")).items()
    }
