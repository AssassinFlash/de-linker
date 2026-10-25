"""Read component identities from the selected producer's frozen layout.

This is a report projection. It neither runs the PV model nor turns a reference
component into a sale product, string design or mounting qualification.
"""

from __future__ import annotations

import math
from typing import cast

from .canonical import Json, Object, digest, encode
from .errors import InvalidInput, VersionUnavailable
from .geometry import panel_poses, read_geometry
from .geometry_documents import ModuleSpec
from .product_sources import ProductSources
from .pv_parameters import PvGenerationParameters
from .pv_profile_artifacts import model_dependencies
from .pv_profile_preparation import PROFILE_PURPOSE
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
) -> Object:
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
    arrays = {array.id: array for array in geometry.arrays}
    specifications = {module.id: module for module in geometry.module_specs}
    components: dict[str, Object] = {}
    for retained_array in retained:
        identifier = str(retained_array["id"])
        array = arrays[identifier]
        identities = included[identifier]
        if (
            retained_array.get("module_ids") != identities
            or type(retained_array.get("module_count")) is not int
            or retained_array.get("module_count") != len(identities)
            or retained_array.get("module_spec_id") != array.module_spec_id
        ):
            raise VersionUnavailable("the saved PV module count or identities differ")
        if identifier not in selected:
            continue
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
    revision = metadata.get("derived_from_revision")
    return {
        "status": "available",
        "scope": "dc_group" if converter_id is not None else "full_model",
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
            "weather_raw": raw_sha256,
            "woo_module": blobs.put_object(proof),
        },
    }
