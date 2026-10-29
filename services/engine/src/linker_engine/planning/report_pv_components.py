"""Read component identities from the selected producer's frozen layout.

This is a report projection. It neither runs the PV model nor turns a reference
component into a sale product, string design or mounting qualification.
"""

from __future__ import annotations

import math
from typing import cast

from .canonical import Json, Object, digest, encode
from .errors import InvalidInput, VersionUnavailable
from .frozen_documents import FrozenDocuments
from .geometric_pv_inputs import PROFILE_PURPOSE as GEOMETRIC_PV_PURPOSE
from .geometric_pv_profile import reference_bundle as geometric_pv_bundle
from .geometry import panel_poses, read_geometry
from .geometry_documents import GeometryDocument, ModuleSpec
from .product_sources import ProductSources
from .pv_parameters import PvGenerationParameters
from .pv_profile_artifacts import model_dependencies
from .pv_profile_preparation import PROFILE_PURPOSE
from .pvgis_reference_profile import PROFILE_PURPOSE as ROOF_AC_PURPOSE
from .pvgis_reference_profile import reference_bundle
from .storage import Blobs


def _object(value: Json) -> Object:
    if not isinstance(value, dict):
        raise VersionUnavailable("the saved PV component source is incomplete")
    return value


def pv_components(
    blobs: Blobs,
    raw_sha256: str,
    metadata: Object,
    *,
    converter_id: str | None = None,
    documents: FrozenDocuments | None = None,
    geometric_bundle: Object | None = None,
) -> Object:
    if metadata.get("profile_type") == GEOMETRIC_PV_PURPOSE:
        if converter_id is not None:
            raise VersionUnavailable(
                "this geometric PV reference exposes AC output only"
            )
        # The caller that already verified the geometric bundle passes it here;
        # a second manifests-and-witness read would only repeat the same work.
        bundle = (
            geometric_bundle
            if geometric_bundle is not None
            else geometric_pv_bundle(blobs, raw_sha256, metadata, documents)
        )
        return saved_roof_components(
            _object(bundle["inputs"])["geometry"],
            _object(bundle["woo_module_inputs"]),
            blobs,
            cast(int, metadata["derived_from_revision"]),
        )
    if metadata.get("profile_type") == ROOF_AC_PURPOSE:
        if converter_id is not None:
            raise VersionUnavailable("an AC reference has no DC converter group")
        # The report already verified this asset for its own section; reuse the
        # same reader instead of verifying the manifest and children again.
        bundle = reference_bundle(blobs, raw_sha256, metadata, documents)
        return _components(
            read_geometry(bundle["geometry"]),
            _object(bundle["woo_module_inputs"]),
            blobs,
            metadata.get("derived_from_revision"),
            selected=None,
            scope="pvgis_roof_ac_reference",
            converter_id=None,
            dependencies={
                **_object(metadata.get("dependencies")),
                "reference_manifest": raw_sha256,
            },
        )
    if metadata.get("profile_type") != PROFILE_PURPOSE:
        return {"status": "unavailable", "reason": "no_saved_layout"}
    proof = metadata.get("woo_module_inputs")
    if not isinstance(proof, dict):
        return {"status": "unavailable", "reason": "no_woo_module_proof"}
    dependencies = model_dependencies(metadata)
    inputs = blobs.object(dependencies["pv_model_inputs"])
    witness = blobs.object(dependencies["pv_model_witness"])
    parameters = PvGenerationParameters.read(inputs.get("parameters"))
    geometry = read_geometry(inputs.get("geometry"))
    details = _object(witness.get("inputs"))
    weather = _object(inputs.get("weather"))
    source = _object(weather.get("source"))
    if (
        inputs.get("schema_version") != 1
        or witness.get("schema_version") != 1
        or inputs.get("kind") != parameters.model
        or witness.get("kind") != parameters.model
        or details.get("input_bundle_sha256") != dependencies["pv_model_inputs"]
        or details.get("geometry_sha256") != metadata.get("geometry_sha256")
        or metadata.get("geometry_sha256") != digest(encode(inputs["geometry"]))
        # Profile metadata binds the original declared project JSON. The
        # producer pins its typed/normalized parameter JSON separately; equal
        # numbers such as 10000 and 10000.0 need not have the same byte hash.
        or details.get("parameters_sha256") != digest(encode(inputs["parameters"]))
        or details.get("weather_original_sha256") != raw_sha256
        or source.get("raw_sha256") != raw_sha256
    ):
        raise VersionUnavailable(
            "the saved PV component layout differs from its result"
        )

    # Use the same included objects as the geometry/producer; excluded slots
    # never become components, and neither area nor kWp is divided by a guess.
    included: dict[str, list[str]] = {}
    for pose in panel_poses(geometry):
        if pose.included:
            included.setdefault(pose.array_id, []).append(pose.id)
    active = set(included)
    rows = witness.get("arrays")
    if not isinstance(rows, list):
        raise VersionUnavailable("the saved PV result has no component identities")
    retained = [_object(row) for row in rows]
    if (
        len(retained) != len(active)
        or {row.get("id") for row in retained} != active
        or {row.array_id for row in parameters.arrays} != active
    ):
        raise VersionUnavailable("the saved PV component arrays differ")
    selected = active
    if converter_id is not None:
        groups = [p for p in parameters.converters if p.id == converter_id]
        if len(groups) != 1:
            raise VersionUnavailable("the selected PV model group is unavailable")
        selected = set(groups[0].array_ids)
        converters = witness.get("converters")
        recorded_groups = (
            [
                row
                for row in converters
                if isinstance(row, dict) and row.get("id") == converter_id
            ]
            if isinstance(converters, list)
            else []
        )
        if (
            not selected
            or len(selected) != len(groups[0].array_ids)
            or not selected.issubset(active)
            or len(recorded_groups) != 1
            or recorded_groups[0].get("array_ids") != groups[0].array_ids
        ):
            raise VersionUnavailable("the selected PV model group has different arrays")
    for retained_array in retained:
        identifier = str(retained_array["id"])
        array = next(a for a in geometry.arrays if a.id == identifier)
        identities = included[identifier]
        if (
            retained_array.get("module_ids") != identities
            or type(retained_array.get("module_count")) is not int
            or retained_array.get("module_count") != len(identities)
            or retained_array.get("module_spec_id") != array.module_spec_id
        ):
            raise VersionUnavailable("the saved PV module count or identities differ")
    return _components(
        geometry,
        proof,
        blobs,
        metadata.get("derived_from_revision"),
        selected=selected,
        scope="dc_group" if converter_id is not None else "full_model",
        converter_id=converter_id,
        dependencies={**dependencies, "weather_raw": raw_sha256},
    )


def saved_roof_components(
    geometry_json: Json, proof: Object, blobs: Blobs, revision: int
) -> Object:
    """Equipment-only reports use the exact roof checked by that saved result."""
    geometry = read_geometry(geometry_json)
    if any(s.permissions.export != "permitted" for s in geometry.sources):
        raise InvalidInput("material exports require permission for the roof sources")
    return _components(
        geometry,
        proof,
        blobs,
        revision,
        selected=None,
        scope="saved_roof",
        converter_id=None,
        dependencies={"geometry": blobs.put_object(cast(Object, geometry_json))},
    )


def _components(
    geometry: GeometryDocument,
    proof: Object,
    blobs: Blobs,
    revision: Json,
    *,
    selected: set[str] | None,
    scope: str,
    converter_id: str | None,
    dependencies: Object,
) -> Object:
    included: dict[str, list[str]] = {}
    for pose in panel_poses(geometry):
        if pose.included:
            included.setdefault(pose.array_id, []).append(pose.id)
    specifications = {module.id: module for module in geometry.module_specs}
    components: dict[str, Object] = {}
    for array in geometry.arrays:
        identifier = array.id
        if identifier not in included or (
            selected is not None and identifier not in selected
        ):
            continue
        identities = included[identifier]
        module: ModuleSpec = specifications[array.module_spec_id]
        if module.source.woo is None:
            return {"status": "unavailable", "reason": "no_woo_module_proof"}
        try:
            ProductSources._check_module(module, proof)
        except InvalidInput as error:
            raise VersionUnavailable(
                "the saved PV module differs from its Woo proof"
            ) from error
        key = module.source.woo.reference_input_id
        if key not in components:
            components[key] = {
                "model": module.model,
                "quantity": 0,
                "stc_power_w": module.stc_power_w,
                "source": module.source.model_dump(mode="json"),
                "array_ids": [],
                "module_ids": [],
            }
        line = components[key]
        line["quantity"] = cast(int, line["quantity"]) + len(identities)
        cast(list[Json], line["array_ids"]).append(identifier)
        cast(list[Json], line["module_ids"]).extend(identities)
    return {
        "status": "available",
        "scope": scope,
        "converter_id": converter_id,
        "layout_revision": revision if type(revision) is int and revision > 0 else None,
        "components": list(components.values()),
        # SI conversion of documented STC watts, not a performance estimate.
        "nameplate_kwp": math.fsum(
            cast(int, line["quantity"]) * cast(float, line["stc_power_w"])
            for line in components.values()
        )
        / 1000,
        "dependencies": {
            **dependencies,
            "woo_module": blobs.put_object(proof),
        },
    }
