"""Resolve explicit profile formats, never infer a role from numbers or a CSV."""

from __future__ import annotations

from .assets import Asset
from .canonical import Object
from .errors import InvalidInput, VersionUnavailable
from .pv_profile import PURPOSE, reference_dependencies
from .storage import Blobs


def profile_dependencies(
    asset: Asset, role: str, inputs: Object, blobs: Blobs
) -> dict[str, str]:
    result = {
        f"{role}.raw": asset.content_sha256,
        f"{role}.metadata": asset.metadata_sha256,
    }
    if asset.purpose == "csv_profile_v1":
        timezone_hash = asset.metadata.get("timezone_rules_sha256")
        if not isinstance(timezone_hash, str):
            raise VersionUnavailable("profile has no pinned timezone rules")
        result[f"{role}.timezone"] = timezone_hash
    elif asset.purpose == PURPOSE and role == "pv_available_ac":
        result.update(
            {
                f"{role}.{name}": value
                for name, value in reference_dependencies(asset, inputs, blobs).items()
            }
        )
    elif asset.purpose != "pvgis_system_profile_v1" or role != "pv_available_ac":
        raise InvalidInput(
            f"{role}: an imported profile of the matching type is required"
        )
    return result
