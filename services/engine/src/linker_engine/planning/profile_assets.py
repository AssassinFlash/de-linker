"""Resolve explicit profile formats, never infer a role from numbers or a CSV."""

from __future__ import annotations

from .assets import Asset
from .canonical import Object
from .errors import EvidenceMissing, InvalidInput, VersionUnavailable
from .geometric_pv_inputs import PROFILE_PURPOSE as GEOMETRIC_PV_PURPOSE
from .geometric_pv_profile import reference_dependencies as geometric_pv_dependencies
from .pv_profile import PURPOSE, reference_dependencies
from .pvgis_reference_profile import PROFILE_PURPOSE as ROOF_AC_PURPOSE
from .pvgis_reference_profile import reference_dependencies as roof_ac_dependencies
from .storage import Blobs


def profile_dependencies(
    asset: Asset, role: str, inputs: Object, blobs: Blobs, *, binding: str | None = None
) -> dict[str, str]:
    name = role if binding is None else binding
    if role == "pv_available_dc" and asset.purpose != PURPOSE:
        raise EvidenceMissing(
            "pv_dc_stage: retained pre-conversion PV producer output required"
        )
    result = {
        f"{name}.raw": asset.content_sha256,
        f"{name}.metadata": asset.metadata_sha256,
    }
    if asset.purpose == "csv_profile_v1":
        timezone_hash = asset.metadata.get("timezone_rules_sha256")
        if not isinstance(timezone_hash, str):
            raise VersionUnavailable("profile has no pinned timezone rules")
        result[f"{name}.timezone"] = timezone_hash
    elif asset.purpose == PURPOSE and role in ("pv_available_ac", "pv_available_dc"):
        result.update(
            {
                f"{name}.{key}": value
                for key, value in reference_dependencies(asset, inputs, blobs).items()
            }
        )
    elif asset.purpose == ROOF_AC_PURPOSE and role == "pv_available_ac":
        result.update(
            {
                f"{name}.{key}": value
                for key, value in roof_ac_dependencies(asset, inputs, blobs).items()
            }
        )
    elif asset.purpose == GEOMETRIC_PV_PURPOSE and role == "pv_available_ac":
        result.update(
            {
                f"{name}.{key}": value
                for key, value in geometric_pv_dependencies(
                    asset, inputs, blobs
                ).items()
            }
        )
    elif asset.purpose != "pvgis_system_profile_v1" or role != "pv_available_ac":
        raise InvalidInput(
            f"{role}: an imported profile of the matching type is required"
        )
    return result
