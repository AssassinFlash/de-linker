"""Owned, version-bound PV reference assets; raw weather is never browser-attested."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from .assets import Asset, Assets
from .canonical import Object, digest, encode
from .energy_inputs import Document
from .errors import InvalidInput, VersionUnavailable
from .power_series import PowerSeries
from .pv_generation import generate_pv
from .pv_parameters import PvGenerationParameters
from .pvgis_response import PvgisCapture
from .pvgis_tmy import tmy_weather
from .pvgis_tmy_request import PvgisTmyInterpretation, PvgisTmyRequest
from .records import Actor
from .storage import Blobs

PURPOSE = "pvlib_reference_profile_v1"


class PvGenerationLimits(Document):
    max_weather_bytes: Annotated[int, Field(strict=True, gt=0)]
    max_weather_rows: Annotated[int, Field(strict=True, gt=0)]
    max_array_steps: Annotated[int, Field(strict=True, gt=0)]


class PvProfileImport:
    def __init__(self, assets: Assets, limits: PvGenerationLimits) -> None:
        self.assets, self.limits = assets, limits

    def reference_profile(
        self,
        actor: Actor,
        project_id: str,
        revision: int,
        content: bytes,
        request: PvgisTmyRequest,
        capture: PvgisCapture,
        interpretation: PvgisTmyInterpretation,
        provenance: Object,
        *,
        key: str,
    ) -> Asset:
        self.assets.check_write(actor, project_id)
        workspace = self.assets.workspace
        project = workspace.get(actor, project_id, revision=revision)
        geometry, parameters = (
            project.inputs.get("geometry"),
            project.inputs.get("pv_generation"),
        )
        logical: Object = {
            "schema": 1,
            "profile_type": PURPOSE,
            "retention": "permanent",
            "provenance": provenance,
            "derived_from_revision": revision,
            "geometry_sha256": digest(encode(geometry)),
            "parameters_sha256": digest(encode(parameters)),
            "weather_request": {**request.model_dump(mode="json")},
            "weather_capture": capture.document(),
            "weather_interpretation": {**interpretation.model_dump(mode="json")},
        }
        previous = self.assets.receipt(
            actor,
            project_id,
            key,
            {
                "content_sha256": digest(content),
                "media_type": "application/json",
                "purpose": PURPOSE,
                "metadata": logical,
            },
        )
        if previous is not None:
            return previous
        weather = tmy_weather(
            content,
            request,
            capture,
            interpretation,
            max_bytes=self.limits.max_weather_bytes,
            max_rows=self.limits.max_weather_rows,
        )
        result = generate_pv(
            geometry,
            weather,
            PvGenerationParameters.read(parameters),
            max_array_steps=self.limits.max_array_steps,
        )
        # Permission was checked before parsing, calculating or publishing bytes.
        inputs_hash = workspace.blobs.put(result.inputs_json)
        witness_hash = workspace.blobs.put(result.witness_json)
        return self.assets.add(
            actor,
            project_id,
            content,
            "application/json",
            PURPOSE,
            {
                **logical,
                "limits": {**self.limits.model_dump(mode="json")},
                "dependencies": {
                    "pv_model_inputs": inputs_hash,
                    "pv_model_witness": witness_hash,
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
            },
            key=key,
            logical_metadata=logical,
        )


def _model_dependencies(metadata: Object) -> dict[str, str]:
    dependencies = metadata.get("dependencies")
    if not isinstance(dependencies, dict) or set(dependencies) != {
        "pv_model_inputs",
        "pv_model_witness",
    }:
        raise VersionUnavailable("PV model input and witness dependencies required")
    if any(not isinstance(value, str) for value in dependencies.values()):
        raise VersionUnavailable("PV model dependency hash required")
    return {name: str(value) for name, value in dependencies.items()}


def reference_dependencies(
    asset: Asset, inputs: Object, blobs: Blobs
) -> dict[str, str]:
    if asset.metadata.get("geometry_sha256") != digest(
        encode(inputs.get("geometry"))
    ) or asset.metadata.get("parameters_sha256") != digest(
        encode(inputs.get("pv_generation"))
    ):
        raise InvalidInput(
            "PV reference is stale for the selected geometry or model parameters"
        )
    pinned = _model_dependencies(asset.metadata)
    model_inputs = blobs.object(pinned["pv_model_inputs"])
    parameters = PvGenerationParameters.read(inputs.get("pv_generation"))
    if encode(model_inputs.get("geometry")) != encode(inputs.get("geometry")) or encode(
        model_inputs.get("parameters")
    ) != encode(parameters.model_dump(mode="json")):
        raise VersionUnavailable("PV model input does not match the frozen project")
    blobs.read(pinned["pv_model_witness"])
    return pinned


def frozen_reference_profile(
    blobs: Blobs, raw_sha256: str, metadata: Object
) -> PowerSeries:
    dependencies = _model_dependencies(metadata)
    inputs_hash, witness_hash = (
        dependencies["pv_model_inputs"],
        dependencies["pv_model_witness"],
    )
    inputs = blobs.object(inputs_hash)
    blobs.read(witness_hash)
    request = PvgisTmyRequest.read(metadata.get("weather_request"))
    capture = PvgisCapture.read(metadata.get("weather_capture"))
    interpretation = PvgisTmyInterpretation.read(metadata.get("weather_interpretation"))
    limits = PvGenerationLimits.read(metadata.get("limits"))
    weather = tmy_weather(
        blobs.read(raw_sha256),
        request,
        capture,
        interpretation,
        max_bytes=limits.max_weather_bytes,
        max_rows=limits.max_weather_rows,
    )
    if encode(weather.document()) != encode(inputs.get("weather")):
        raise VersionUnavailable("PV input weather differs from its frozen original")
    result = generate_pv(
        inputs.get("geometry"),
        weather,
        PvGenerationParameters.read(inputs.get("parameters")),
        max_array_steps=limits.max_array_steps,
    )
    if (
        digest(result.inputs_json) != inputs_hash
        or digest(result.witness_json) != witness_hash
    ):
        raise VersionUnavailable("the pinned PV reference witness cannot be reproduced")
    return result.profile
