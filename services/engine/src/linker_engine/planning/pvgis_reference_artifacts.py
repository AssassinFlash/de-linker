"""One all-or-nothing roof reference bundle retaining each official original."""

import logging
import math
from collections.abc import Callable
from typing import cast

from .asset_publication import AssetPublication
from .canonical import Json, Object, encode
from .errors import InvalidInput
from .power_series import PowerSeries
from .pvgis_known_inputs import MODEL as KNOWN_MODEL
from .pvgis_known_inputs import MODEL_ROLE as KNOWN_ROLE
from .pvgis_known_inputs import PROFILE_PURPOSE as KNOWN_PURPOSE
from .pvgis_known_inputs import KnownPvPlan, KnownPvRequest
from .pvgis_profile import pvgis_profile
from .pvgis_reference_array import PvgisReferenceArray
from .pvgis_reference_download import ReferenceCapture
from .pvgis_reference_plan import PvgisReferencePlan
from .pvgis_response import read_pvgis
from .storage import Blobs

PROFILE_PURPOSE = "pvgis_roof_ac_reference_profile_v1"
LOG = logging.getLogger(__name__)


def prepare_reference_asset(
    blobs: Blobs,
    project_id: str,
    revision: int,
    inputs: Object,
    basis: Object,
    plan: PvgisReferencePlan | KnownPvPlan,
    captures: list[ReferenceCapture],
    *,
    guard: Callable[[], None] = lambda: None,
    acquisition: Object | None = None,
) -> tuple[AssetPublication, Object]:
    if len(captures) != len(plan.arrays):
        raise InvalidInput("every roof array needs its own complete official response")
    plan_sha = blobs.put_object(plan.document())
    known = isinstance(plan, KnownPvPlan)
    purpose = KNOWN_PURPOSE if known else PROFILE_PURPOSE
    model_role = KNOWN_ROLE if known else "official_calendar_year_roof_ac_reference"
    dependencies: Object = {
        "reference_plan": plan_sha,
        "reference_parameters": blobs.put_object(
            cast(Object, inputs["pvgis_reference"])
        ),
    }
    if isinstance(plan, KnownPvPlan):
        dependencies["reference_site"] = blobs.put_object(
            plan.site.model_dump(mode="json")
        )
        binding: Object = {
            "site_sha256": plan.site_sha256,
            "basis": "customer_declared",
        }
    else:
        dependencies["reference_geometry"] = blobs.put_object(
            cast(Object, inputs["geometry"])
        )
        dependencies["reference_woo_module"] = blobs.put_object(basis)
        binding = {
            "geometry_sha256": plan.geometry_sha256,
            "module_basis_sha256": plan.module_basis_sha256,
        }
    arrays: list[Json] = []
    profiles: list[PowerSeries] = []
    requests = cast(list[PvgisReferenceArray | KnownPvRequest], plan.arrays)
    for index, (array, source) in enumerate(zip(requests, captures, strict=True)):
        guard()
        raw_sha = blobs.put(source.content)
        capture_sha = blobs.put_object(source.capture.document())
        # Private operational provenance preserves a failed parse's original
        # lookup without exposing URL/coordinates or creating a usable asset.
        LOG.info(
            "PVGIS reference original plan=%s array=%s raw=%s capture=%s",
            plan_sha,
            array.id,
            raw_sha,
            capture_sha,
        )
        if (
            source.capture.capture_basis != "official_jrc_https_get_original_v1"
            or source.capture.source_identifiers
            != {"provider": "EC_JRC_PVGIS", "api_version": "5.3"}
        ):
            raise InvalidInput(
                "managed roof reference requires server-authored official capture"
            )
        native = read_pvgis(
            source.content,
            array.request,
            source.capture,
            max_bytes=plan.limits.max_response_bytes,
            max_rows=plan.limits.max_weather_rows,
        )
        profile = pvgis_profile(native, plan.parameters.interpretation())
        guard()
        if profiles and profile.intervals != profiles[0].intervals:
            raise InvalidInput(
                "roof reference arrays must use exactly the same interval axis"
            )
        profiles.append(profile)
        dependencies[f"array.{index}.original"] = raw_sha
        dependencies[f"array.{index}.capture"] = capture_sha
        arrays.append(
            {
                **array.model_dump(mode="json"),
                "original_sha256": raw_sha,
                "capture_sha256": capture_sha,
                "native_value_semantics": native.value_semantics,
                "interpretation": plan.parameters.interpretation().document(),
                "source_document": native.source_document(),
                "energy_kwh": profile.total_kwh,
            }
        )
    axis: list[Json] = [
        {"start_utc": interval.start.isoformat(), "end_utc": interval.end.isoformat()}
        for interval in profiles[0].intervals
    ]
    powers = [math.fsum(p.values_kw[i] for p in profiles) for i in range(len(axis))]
    guard()
    energy = math.fsum(powers)  # Every validated native interval is one hour.
    if not math.isfinite(energy):
        raise InvalidInput("roof reference aggregate energy is not finite")
    witness: Object = {
        "schema_version": 1,
        "kind": "pvgis_5_3_roof_ac_reference_output_v1",
        "plan_sha256": plan_sha,
        "intervals": axis,
        "available_ac_kw": cast(Json, powers),
        "energy_kwh": energy,
        "transformations": [t.document() for p in profiles for t in p.transformations],
    }
    output_sha = blobs.put_object(witness)
    dependencies["reference_output"] = output_sha
    manifest: Object = {
        "schema_version": 1,
        "kind": KNOWN_MODEL if known else "pvgis_5_3_roof_ac_reference_v1",
        "plan_sha256": plan_sha,
        **binding,
        "parameters_sha256": plan.parameters_sha256,
        "arrays": arrays,
        "output_sha256": output_sha,
    }
    summary: Object = {
        "start_utc": profiles[0].intervals[0].start.isoformat(),
        "end_utc": profiles[0].intervals[-1].end.isoformat(),
        "interval_count": len(axis),
        "energy_kwh": energy,
        "measurement": "pv_available_ac",
        "origin": "modelled",
        "native_max_interval_seconds": 3600,
        "reconstructed_means": any(p.reconstructed_means for p in profiles),
        "model_role": model_role,
    }
    metadata: Object = {
        "schema": 1,
        "profile_type": purpose,
        "retention": "permanent",
        "derived_from_revision": revision,
        **(
            {"basis": "customer_declared", "site_sha256": binding["site_sha256"]}
            if known
            else {
                "geometry_sha256": binding["geometry_sha256"],
                "woo_module_inputs": basis,
            }
        ),
        "parameters_sha256": plan.parameters_sha256,
        "dependencies": dependencies,
        "interpretation": summary,
        "provenance": {
            "label": "JRC PVGIS customer-declared AC reference"
            if known
            else "JRC PVGIS calendar-year roof AC reference",
            "basis": "Official modelled system output; selected year and model assumptions, not measured generation or specific-device performance",
            "rights_basis": "JRC PVGIS usage conditions; source attribution and private permanent original retention",
        },
    }
    if acquisition is not None:
        metadata["acquisition"] = acquisition
    return (
        AssetPublication.prepare(
            blobs,
            project_id,
            encode(manifest),
            "application/json",
            purpose,
            metadata,
        ),
        summary,
    )
