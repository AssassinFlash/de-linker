"""Owned, version-bound PV reference assets; raw weather is never browser-attested."""

from __future__ import annotations

from .assets import Asset, Assets
from .canonical import Object, digest, encode
from .errors import InvalidInput, VersionUnavailable
from .power_series import PowerSeries
from .pv_generation import generate_pv
from .pv_parameters import PvGenerationLimits as PvGenerationLimits
from .pv_parameters import PvGenerationParameters
from .pv_profile_artifacts import model_dependencies
from .pv_profile_preparation import PROFILE_PURPOSE, logical_profile, prepare_profile
from .pv_source import PvSource
from .pvgis_response import PvgisCapture
from .pvgis_tmy import tmy_weather
from .pvgis_tmy_request import PvgisTmyInterpretation, PvgisTmyRequest
from .records import Actor
from .storage import Blobs

PURPOSE = PROFILE_PURPOSE


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
        source = PvSource(content, request, capture, interpretation, encode(provenance))
        logical = logical_profile(project.inputs, revision, source)
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
        # Permission was checked before parsing, calculating or publishing bytes.
        metadata = prepare_profile(
            workspace.blobs, project.inputs, revision, source, self.limits
        )
        return self.assets.add(
            actor,
            project_id,
            content,
            "application/json",
            PURPOSE,
            metadata,
            key=key,
            logical_metadata=logical,
        )


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
    pinned = model_dependencies(asset.metadata)
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
    dependencies = model_dependencies(metadata)
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
