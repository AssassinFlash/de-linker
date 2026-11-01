"""Export the already frozen series witness on the same report revision."""

from __future__ import annotations

import csv
import io
import json
from typing import cast

from .canonical import Json, Object
from .errors import VersionUnavailable
from .geometric_pv_inputs import MODEL_V3
from .geometric_pv_profile import prepared_profile, reference_bundle
from .storage import Blobs


def _cell(value: object) -> object:
    # Project-supplied identifiers must remain data in spreadsheet programs.
    return (
        "'" + value
        if isinstance(value, str) and value.startswith(("=", "+", "-", "@"))
        else value
    )


def _array(values: object) -> str:
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"))


def series_csv(blobs: Blobs, references: list[Json]) -> bytes | None:
    """One row per timestamp and string; module conditions use matching JSON arrays.

    Module IDs and condition arrays share an order. Values come from the original
    model witness; neither the model nor the weather provider is run again.
    """
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        (
            "scenario_asset_id",
            "model",
            "start_utc",
            "end_utc",
            "string_id",
            "mppt",
            "input",
            "module_ids_json",
            "effective_irradiance_w_m2_json",
            "cell_temperature_c_json",
            "direct_beam_visible_fraction_json",
            "string_voltage_v",
            "string_current_a",
            "string_dc_after_wiring_w",
            "scenario_total_ac_w",
            "tracker_min_voltage_v",
            "tracker_max_voltage_v",
            "tracker_max_current_a",
        )
    )
    found = False
    for raw in references:
        if not isinstance(raw, dict) or raw.get("model") != MODEL_V3:
            continue
        found = True
        reference = raw
        metadata = blobs.object(str(reference["metadata_sha256"]))
        sha = str(reference["content_sha256"])
        bundle = reference_bundle(blobs, sha, metadata)
        profile = prepared_profile(blobs, sha, metadata, bundle=bundle)
        witness = cast(Object, bundle["witness"])
        modules = {
            str(row["module_id"]): row for row in cast(list[Object], witness["modules"])
        }
        for string in cast(list[Object], witness["strings"]):
            window = cast(list[Json], string["window_v"])
            ids = cast(list[str], string["module_ids"])
            selected = [modules[module_id] for module_id in ids]
            ids_json = _array(ids)
            for index, interval in enumerate(profile.intervals):
                try:
                    conditions = [
                        _array(
                            [
                                cast(list[Json], module[field])[index]
                                for module in selected
                            ]
                        )
                        for field in (
                            "effective_irradiance_w_m2",
                            "cell_temperature_c",
                            "direct_beam_visible_fraction",
                        )
                    ]
                    row = (
                        reference["asset_id"],
                        MODEL_V3,
                        interval.start.isoformat(),
                        interval.end.isoformat(),
                        string["id"],
                        string["mppt"],
                        string["input"],
                        ids_json,
                        *conditions,
                        cast(list[Json], string["voltage_v"])[index],
                        cast(list[Json], string["current_a"])[index],
                        cast(list[Json], string["dc_available_w"])[index],
                        cast(list[Json], witness["available_ac_w"])[index],
                        window[0],
                        window[1],
                        string["maximum_current_a"],
                    )
                except (IndexError, KeyError, TypeError) as error:
                    raise VersionUnavailable(
                        "incomplete frozen series witness"
                    ) from error
                writer.writerow([_cell(value) for value in row])
    return output.getvalue().encode("utf-8") if found else None
