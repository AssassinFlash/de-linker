"""Project each retained PV group once, preserving its AC or pre-AC stage."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .canonical import Json, Object, decode_object, encode
from .dc_plant_inputs import DcPlantEnergyInputs
from .errors import InvalidInput, VersionUnavailable
from .power_series import PowerSeries
from .pv_dc_profile import DcPvProfile, project_dc
from .pv_parameters import PvGenerationParameters
from .pv_profile_artifacts import model_dependencies, prepared_profile
from .series_source import SeriesSource
from .storage import Blobs


@dataclass(frozen=True)
class PlantPvProfiles:
    dc: dict[str, DcPvProfile]
    ac: PowerSeries | None


def _power(value: Json) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise VersionUnavailable("a finite nonnegative retained AC power is required")
    return float(value)


def project(
    blobs: Blobs, raw_sha256: str, metadata: Object, scenario: DcPlantEnergyInputs
) -> PlantPvProfiles:
    # The existing producer verifies hashes, original weather, time axis and
    # model witness once. Group projection never repeats weather/PV modelling.
    ac = prepared_profile(blobs, raw_sha256, metadata)
    dependencies = model_dependencies(metadata)
    inputs, witness = (
        blobs.object(dependencies["pv_model_inputs"]),
        blobs.object(dependencies["pv_model_witness"]),
    )
    parameters = PvGenerationParameters.read(inputs.get("parameters"))
    selected = [
        u.pv_converter_id for u in scenario.units if u.pv_converter_id is not None
    ] + scenario.ac_pv_converter_ids
    if set(selected) != {g.id for g in parameters.converters} or len(selected) != len(
        parameters.converters
    ):
        raise InvalidInput(
            "assign every retained PV group once to a DC unit or the separate AC bus"
        )
    dc = {
        u.unit_id: project_dc(
            ac, inputs, witness, dependencies["pv_model_witness"], u.pv_converter_id
        )
        for u in scenario.units
        if u.pv_converter_id is not None
    }
    if not scenario.ac_pv_converter_ids:
        return PlantPvProfiles(dc, None)
    # Apply the same exact group/array cross-binding as the DC projection.
    # These AC values are the producer's own retained outputs, never DC/eta.
    retained = witness.get("converters")
    if not isinstance(retained, list):
        raise VersionUnavailable("PV conversion outputs are absent")
    outputs = []
    for identifier in scenario.ac_pv_converter_ids:
        project_dc(ac, inputs, witness, dependencies["pv_model_witness"], identifier)
        matches = [
            row
            for row in retained
            if isinstance(row, dict) and row.get("id") == identifier
        ]
        values = matches[0].get("available_ac_w") if len(matches) == 1 else None
        if not isinstance(values, list) or len(values) != len(ac.intervals):
            raise VersionUnavailable(
                "each assigned AC group needs its complete retained output"
            )
        outputs.append([_power(v) for v in values])
    details = decode_object(ac.source.details_json)
    details.update(
        {
            "converter_ids": list(scenario.ac_pv_converter_ids),
            "output_boundary": "retained_selected_converter_ac_outputs",
            "model_witness_sha256": dependencies["pv_model_witness"],
        }
    )
    profile = PowerSeries(
        ac.intervals,
        tuple(
            math.fsum(float(row[i]) for row in outputs) / 1000
            for i in range(len(ac.intervals))
        ),
        "pv_available_ac",
        SeriesSource(
            ac.source.raw_sha256,
            ac.source.origin,
            ac.source.timezone,
            ac.source.native_max_interval_seconds,
            encode(details),
        ),
        ac.transformations,
    )
    return PlantPvProfiles(dc, profile)
