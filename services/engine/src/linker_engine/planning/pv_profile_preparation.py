"""Prepare reference metadata and immutable children without publishing an owner row."""

from __future__ import annotations

from .canonical import Object, digest, encode
from .pv_generation import generate_pv
from .pv_parameters import PvGenerationLimits, PvGenerationParameters
from .pv_source import PvSource
from .storage import Blobs

PROFILE_PURPOSE = "pvlib_reference_profile_v1"


def logical_profile(inputs: Object, revision: int, source: PvSource) -> Object:
    return {
        "schema": 1,
        "profile_type": PROFILE_PURPOSE,
        "retention": "permanent",
        **source.metadata(),
        "derived_from_revision": revision,
        "geometry_sha256": digest(encode(inputs.get("geometry"))),
        "parameters_sha256": digest(encode(inputs.get("pv_generation"))),
    }


def prepare_profile(
    blobs: Blobs,
    inputs: Object,
    revision: int,
    source: PvSource,
    limits: PvGenerationLimits,
) -> Object:
    weather = source.weather(limits)
    result = generate_pv(
        inputs.get("geometry"),
        weather,
        PvGenerationParameters.read(inputs.get("pv_generation")),
        max_array_steps=limits.max_array_steps,
    )
    return {
        **logical_profile(inputs, revision, source),
        "limits": {**limits.model_dump(mode="json")},
        "dependencies": {
            "pv_model_inputs": blobs.put(result.inputs_json),
            "pv_model_witness": blobs.put(result.witness_json),
        },
        "interpretation": {
            "start_utc": result.profile.intervals[0].start.isoformat(),
            "end_utc": result.profile.intervals[-1].end.isoformat(),
            "interval_count": len(result.profile.intervals),
            "energy_kwh": result.profile.total_kwh,
            "measurement": "pv_available_ac",
            "origin": "modelled",
            "native_max_interval_seconds": weather.source.native_max_interval_seconds,
            "reconstructed_means": True,
            "transformations": [
                item.document() for item in result.profile.transformations
            ],
            "model_role": "unshaded_reference_scenario",
        },
    }
