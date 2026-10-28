"""Pure geometric preparation from exact frozen caller-owned source reads.

Missing native owner resolution/current Woo confirmation/publication fencing
cannot be replaced by this function: it neither authenticates nor publishes.
It returns a geometric document, never a PowerSeries or usable PV profile.
"""

from __future__ import annotations

import math

import pvlib
import shapely

from .canonical import Json, Object, decode_object, digest, encode
from .direct_beam_geometry import ULP_ALLOWANCE, build_scene
from .direct_beam_index import DirectBeamIndex
from .direct_beam_inputs import (
    DirectBeamBinding,
    DirectBeamLimits,
    DirectBeamSampling,
    FrozenWeatherSelection,
)
from .direct_beam_visibility import VisibilityBudget, visibility_row
from .errors import InvalidInput
from .geometry import read_geometry, sin_cos_degrees
from .product_sources import ProductSources
from .pv_conventions import CONVENTIONS
from .pv_physics import sun
from .pv_weather import WeatherSeries


def prepare_direct_beam(
    geometry_value: Json,
    woo_module_basis: Object,
    weather: WeatherSeries,
    weather_asset_metadata: Object,
    selection: FrozenWeatherSelection,
    binding: DirectBeamBinding,
    sampling: DirectBeamSampling,
    limits: DirectBeamLimits,
) -> Object:
    """Caller must supply all hash-bound reads; no fetch/default/fallback path."""
    # Canonical owned copies prevent later caller edits from changing the
    # document whose hash was checked. No copy is written to disk or CAS.
    geometry_bytes, basis_bytes = encode(geometry_value), encode(woo_module_basis)
    geometry_value = decode_object(geometry_bytes)
    woo_module_basis = decode_object(basis_bytes)
    selection = FrozenWeatherSelection.read(selection.model_dump(mode="json"))
    expected = {
        "geometry_sha256": digest(geometry_bytes),
        "woo_module_basis_sha256": digest(basis_bytes),
        "weather_asset_metadata_sha256": digest(encode(weather_asset_metadata)),
        "weather_document_sha256": digest(encode(weather.document())),
        "weather_selection_sha256": digest(encode(selection.model_dump(mode="json"))),
    }
    if (
        any(getattr(binding, key) != value for key, value in expected.items())
        or selection.project_id != binding.project_id
        or selection.project_revision != binding.project_revision
        or selection.weather_document_sha256 != binding.weather_document_sha256
        or selection.asset_metadata_sha256 != binding.weather_asset_metadata_sha256
    ):
        raise InvalidInput("direct-beam frozen source binding differs")
    if len(selection.row_indices) > limits.max_selected_rows or selection.row_indices[
        -1
    ] >= len(weather.points):
        raise InvalidInput("direct-beam source row selection exceeds its domain")
    # This checks the frozen exact Woo geometry reference. Current publication
    # permission must still be confirmed by the native worker at intake
    # and immediately before publication, just like existing PV preparation.
    ProductSources.check_roof_inputs({"geometry": geometry_value}, woo_module_basis)
    geometry = read_geometry(geometry_value)
    anchor = geometry.coordinate_system.anchor
    if (
        anchor is None
        or geometry.coordinate_system.north_reference == "unreferenced"
        or (anchor.latitude_deg, anchor.longitude_deg)
        != (weather.latitude_deg, weather.longitude_deg)
    ):
        raise InvalidInput(
            "direct-beam weather requires the frozen geographic/north binding"
        )
    scene = build_scene(geometry_value)
    samples = (
        (sampling.coarse_cells_per_edge**2 + sampling.fine_cells_per_edge**2)
        * len(scene.receivers)
        * len(selection.row_indices)
    )
    if samples > limits.max_samples:
        raise InvalidInput("direct-beam requested sampling exceeds its resource budget")
    spatial_index = DirectBeamIndex.from_scene(scene, leaf_size=limits.index_leaf_size)
    selected = WeatherSeries(
        weather.latitude_deg,
        weather.longitude_deg,
        weather.altitude_m,
        tuple(weather.points[index] for index in selection.row_indices),
        weather.source,
    )
    position = sun(
        selected
    )  # Existing pinned SPA uses irradiance_at_utc, not interval labels.
    budget = VisibilityBudget(limits)
    rows: list[Json] = []
    for ordinal, (index, point) in enumerate(
        zip(selection.row_indices, selected.points, strict=True)
    ):
        zenith = float(position["apparent_zenith_deg"][ordinal])
        azimuth = float(position["azimuth_deg"][ordinal])
        sz, cz = sin_cos_degrees(zenith)
        sa, ca = sin_cos_degrees(azimuth)
        direction = (sz * sa, sz * ca, cz)
        if not all(math.isfinite(value) for value in direction):
            raise InvalidInput("direct-beam solar position is nonfinite")
        rows.append(
            {
                "source_row_index": index,
                "interval_start_utc": point.interval.start.isoformat(),
                "interval_end_utc": point.interval.end.isoformat(),
                "source_label_utc": point.source_label_utc.isoformat(),
                "irradiance_at_utc": point.irradiance_at_utc.isoformat(),
                "apparent_zenith_deg": zenith,
                "azimuth_north_clockwise_deg": azimuth,
                "delta_t_seconds": float(position["delta_t_seconds"][ordinal]),
                "sun_direction_enu": list(direction),
                # DNI zero never suppresses an otherwise valid geometric result.
                **visibility_row(
                    scene, direction, sampling, budget, index=spatial_index
                ),
            }
        )
    return {
        "schema_version": 1,
        "kind": "geometric_direct_beam_visibility_v1",
        "method": "declared_opaque_ray_midpoint_uvn_v1",
        "publication_status": "geometry_witness_not_a_power_profile",
        "sources": binding.model_dump(mode="json"),
        "owned_weather_selection": selection.model_dump(mode="json"),
        "sampling": {
            **sampling.model_dump(mode="json"),
            "method": "equal_area_midpoints",
            "sample_count": budget.samples,
            "ray_face_checks": budget.ray_face_checks,
            "bounds_checks": budget.bounds_checks,
            "delta_interpretation": "observed_resolution_difference_not_error_bound",
        },
        "limits": limits.model_dump(mode="json"),
        "spatial_index": {
            "method": "closed_outward_rounded_aabb_bvh_v1",
            "leaf_size": limits.index_leaf_size,
            "scope": "candidates_only_exact_intersections_retained",
        },
        "geometry_library": {
            "shapely": shapely.__version__,
            "geos": shapely.geos_version_string,
        },
        "arithmetic": {
            "frame": "rebased_roof_uvn",
            "guard_ulp_allowance": ULP_ALLOWANCE,
            "guard_m": scene.epsilon_m,
        },
        "solar_position": {
            "pvlib_version": pvlib.__version__,
            "method": CONVENTIONS.solar_position,
            "delta_t": CONVENTIONS.delta_t,
            "time_basis": "irradiance_at_utc",
            "zenith": "apparent",
            "north_reference": geometry.coordinate_system.north_reference,
        },
        "assumptions": [
            "declared_roof_surfaces_and_holes_are_opaque_surfaces_only",
            "declared_obstacle_extrusions_and_included_module_cuboids_are_opaque",
            "only_the_receiving_module_itself_is_excluded",
            "no_undeclared_building_volume_or_transparency",
            "no_diffuse_reflection_diffraction_or_electrical_loss_model",
            "fractions_are_geometric_not_power_or_energy_losses",
        ],
        "excluded_nonopaque_keepout_ids": list(scene.excluded_nonopaque_ids),
        "required_native_integration": [
            "resolve_owned_project_revision_and_weather_asset",
            "confirm_current_woo_module_permission_at_intake_and_publication",
            "retain_exact_hashed_input_documents",
            "freeze_execution_identity_and_fence_native_artifact_publication",
        ],
        "authorization": "not_performed_by_this_pure_geometry_core",
        "rows": rows,
    }
