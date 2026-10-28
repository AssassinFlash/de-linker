"""The one projection of saved array identities used by PV reference sections.

The retained witness carries the array's declared model facts; its placement in
the frozen geometry carries the mounting note and clearance. Both the unshaded
and the geometric reference sections report exactly these fields, so the
projection lives here instead of being rewritten per section.
"""

from __future__ import annotations

from .canonical import Json, Object
from .errors import VersionUnavailable

ARRAY_FIELDS = (
    "id",
    "module_spec_id",
    "module_count",
    "stc_power_w",
    "normal_enu",
    "tilt_deg",
    "azimuth_north_clockwise_deg",
    "azimuth_basis",
)


def _object(value: Json) -> Object:
    if not isinstance(value, dict):
        raise VersionUnavailable("the frozen PV array document is incomplete")
    return value


def array_identities(
    arrays: list[Json],
    placements: list[Json],
    *,
    selected: set[str] | None = None,
) -> list[Json]:
    """Project witness arrays onto their frozen placements, in witness order."""
    placed = {str(_object(item)["id"]): _object(item) for item in placements}
    result: list[Json] = []
    for value in arrays:
        array = _object(value)
        identifier = str(array["id"])
        if selected is not None and identifier not in selected:
            continue
        placement = placed.get(identifier)
        if placement is None:
            raise VersionUnavailable("the saved PV array has no frozen placement")
        result.append(
            {
                **{key: array[key] for key in ARRAY_FIELDS},
                "mounting_note": placement.get("mounting_note"),
                "lower_edge_clearance_m": placement.get("lower_edge_clearance_m"),
            }
        )
    return result


def placements_of(geometry: Object) -> list[Json]:
    arrays = geometry.get("arrays")
    if not isinstance(arrays, list):
        raise VersionUnavailable("the frozen PV geometry has no arrays")
    return arrays
