"""Read a retained geometric witness without recomputing or changing its source."""

from __future__ import annotations

from typing import cast

from .canonical import Json, Object
from .direct_beam_inputs import (
    DirectBeamBinding,
    DirectBeamTaskInputs,
    FrozenWeatherSelection,
)
from .errors import VersionUnavailable
from .product_sources import ProductSources
from .records import Run
from .workspace import Workspace

KIND = "prepare_direct_beam_visibility_v1"


def direct_beam_bundle(workspace: Workspace, run: Run) -> Object:
    result = run.result
    if run.state != "succeeded" or result is None or result.get("kind") != KIND:
        raise VersionUnavailable(
            "a completed geometric direct-beam witness is required"
        )
    if any(
        result.get(key) != value
        for key, value in {
            "project_id": run.project_id,
            "revision": run.revision,
            "manifest_sha256": run.manifest_sha256,
            "input_sha256": run.manifest.get("input_sha256"),
        }.items()
    ):
        raise VersionUnavailable("geometric witness differs from its saved calculation")
    pinned, dependencies, witness = (
        result.get("pinned_assets"),
        result.get("dependencies"),
        result.get("visibility"),
    )
    if (
        not isinstance(pinned, dict)
        or not isinstance(dependencies, dict)
        or not isinstance(witness, dict)
    ):
        raise VersionUnavailable("geometric witness source bindings are missing")
    for key, sha in dependencies.items():
        if not isinstance(sha, str) or (key in pinned and pinned[key] != sha):
            raise VersionUnavailable("geometric witness dependencies differ")
        workspace.blobs.read(sha)
    context = run.manifest.get("context")
    if not isinstance(context, dict) or context.get("assets") != pinned:
        raise VersionUnavailable(
            "geometric witness differs from its admitted source snapshot"
        )
    required = {
        "runtime_bundle",
        "weather.raw",
        "weather.metadata",
        "geometry",
        "woo.module_inputs",
        "weather.document",
        "weather.selection",
    }
    if set(dependencies) != required or set(pinned) != required - {
        "weather.document",
        "weather.selection",
    }:
        raise VersionUnavailable("complete geometric witness sources required")
    geometry = workspace.blobs.object(cast(str, dependencies["geometry"]))
    basis = workspace.blobs.object(cast(str, dependencies["woo.module_inputs"]))
    weather = workspace.blobs.object(cast(str, dependencies["weather.document"]))
    metadata = workspace.blobs.object(cast(str, dependencies["weather.metadata"]))
    selection_document = workspace.blobs.object(
        cast(str, dependencies["weather.selection"])
    )
    selection = FrozenWeatherSelection.read(selection_document)
    binding = DirectBeamBinding.read(witness.get("sources"))
    inputs = workspace.pinned_inputs(run.manifest)
    request = DirectBeamTaskInputs.read(inputs.get("direct_beam_visibility"))
    sampling = witness.get("sampling")
    if not isinstance(sampling, dict):
        raise VersionUnavailable("geometric witness sampling is missing")
    with workspace.database.read() as connection:
        asset = connection.execute(
            "SELECT content_sha256,metadata_sha256 FROM project_assets WHERE project_id=? AND id=?",
            (run.project_id, selection.asset_id),
        ).fetchone()
    if (
        asset is None
        or asset["content_sha256"] != dependencies["weather.raw"]
        or asset["metadata_sha256"] != dependencies["weather.metadata"]
    ):
        raise VersionUnavailable(
            "geometric witness no longer matches its owned weather asset"
        )
    if (
        result.get("frozen_geometry") != geometry
        or inputs.get("geometry") != geometry
        or selection.asset_id != request.weather_asset_id
        or selection.row_indices != request.row_indices
        or sampling.get("coarse_cells_per_edge")
        != request.sampling.coarse_cells_per_edge
        or sampling.get("fine_cells_per_edge") != request.sampling.fine_cells_per_edge
        or witness.get("owned_weather_selection") != selection_document
        or selection.project_id != run.project_id
        or selection.project_revision != run.revision
        or binding.project_id != run.project_id
        or binding.project_revision != run.revision
        or binding.geometry_sha256 != dependencies["geometry"]
        or binding.woo_module_basis_sha256 != dependencies["woo.module_inputs"]
        or binding.weather_document_sha256 != dependencies["weather.document"]
        or binding.weather_asset_metadata_sha256 != dependencies["weather.metadata"]
        or binding.weather_selection_sha256 != dependencies["weather.selection"]
        or selection.asset_metadata_sha256 != dependencies["weather.metadata"]
        or selection.weather_document_sha256 != dependencies["weather.document"]
    ):
        raise VersionUnavailable(
            "geometric witness differs from its frozen input selection"
        )
    source = weather.get("source")
    if (
        not isinstance(source, dict)
        or source.get("raw_sha256") != dependencies["weather.raw"]
    ):
        raise VersionUnavailable("geometric witness weather original differs")
    ProductSources.check_roof_inputs(inputs, basis)
    rows = witness.get("rows")
    points = weather.get("points")
    if (
        not isinstance(rows, list)
        or not isinstance(points, list)
        or len(rows) != len(selection.row_indices)
    ):
        raise VersionUnavailable("geometric witness selected rows differ")
    for index, row in zip(selection.row_indices, rows, strict=True):
        if (
            not isinstance(row, dict)
            or index >= len(points)
            or not isinstance(points[index], dict)
        ):
            raise VersionUnavailable("geometric witness selected row is missing")
        point = cast(Object, points[index])
        if row.get("source_row_index") != index or any(
            row.get(key) != point.get(native)
            for key, native in (
                ("interval_start_utc", "start_utc"),
                ("interval_end_utc", "end_utc"),
                ("source_label_utc", "source_label_utc"),
                ("irradiance_at_utc", "irradiance_at_utc"),
            )
        ):
            raise VersionUnavailable(
                "geometric witness time axes differ from retained weather"
            )
    return {
        "witness": witness,
        "geometry": geometry,
        "woo_module_inputs": basis,
        "weather_metadata": metadata,
        "dependencies": dependencies,
    }


def direct_beam_facts(witness: Object) -> Object:
    """Typed aggregate facts; no editable IDs, notes, exact location or URLs."""
    facts: list[Json] = []
    for row in cast(list[Object], witness["rows"]):
        modules = cast(list[Object], row["modules"])
        fine = [
            cast(Object, module["fine"])["visible_fraction"]
            for module in modules
            if module["status"] == "sampled"
        ]
        delta = [
            cast(float, module["observed_absolute_delta"])
            for module in modules
            if module["status"] == "sampled"
        ]
        facts.append(
            {
                **{
                    key: row[key]
                    for key in (
                        "interval_start_utc",
                        "interval_end_utc",
                        "source_label_utc",
                        "irradiance_at_utc",
                    )
                },
                "module_count": len(modules),
                "sampled_module_count": len(fine),
                "night_module_count": sum(
                    module["status"] == "night" for module in modules
                ),
                "back_facing_or_tangent_module_count": sum(
                    module["status"] == "back_facing_or_tangent" for module in modules
                ),
                "fine_visible_fraction_min": min(cast(list[float], fine))
                if fine
                else None,
                "fine_visible_fraction_max": max(cast(list[float], fine))
                if fine
                else None,
                "observed_absolute_delta_max": max(delta) if delta else None,
            }
        )
    return {
        "kind": witness["kind"],
        "method": witness["method"],
        "scope": "selected_rows_geometric_fraction_not_power_loss_or_annual_energy",
        "sampling": witness["sampling"],
        "limits": witness["limits"],
        "solar_position": {
            key: cast(Object, witness["solar_position"])[key]
            for key in ("pvlib_version", "method", "time_basis", "zenith")
        },
        "equipment_release": "not_assessed",
        "country_assessment": "not_assessed",
        "complete_shading_assessment": "not_assessed",
        "rows": facts,
    }
