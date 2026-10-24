"""Frozen source acquisition publishes only with its successful durable job."""

from __future__ import annotations

from collections.abc import Callable

from requests.adapters import BaseAdapter

from .apify_transport import ApifyTransport
from .apify_weather_client import ApifyWeatherClient
from .asset_publication import AssetPublication, AssetResult
from .canonical import Object, encode
from .errors import VersionUnavailable
from .execution_identity import execution_key, request_execution_key
from .frozen_run import frozen_manifest
from .records import Context, Lease
from .runtime_snapshot import RuntimeSnapshot
from .weather_acquisition import WeatherAcquisition
from .weather_connection import apify_credential
from .weather_fetch_plan import WeatherFetchLimits, WeatherFetchPlan
from .weather_inputs import WeatherAcquisitionInputs
from .weather_journal import WeatherJournal
from .weather_metadata import WEATHER_PURPOSE, weather_details, weather_identity
from .worker import Control
from .workspace import Workspace


class WeatherKernel:
    kind = "acquire_pvgis_tmy_weather_v1"
    models = {
        "task": kind,
        "weather": "pvgis_5_3_tmy_explicit_two_axes_v1",
        "acquisition": "pinned_apify_correlated_original_v1",
    }

    def __init__(
        self,
        workspace: Workspace,
        limits: WeatherFetchLimits,
        *,
        credential: Callable[[], str] = apify_credential,
        adapter_factory: Callable[[], BaseAdapter] | None = None,
    ) -> None:
        self.workspace = workspace
        self.limits = WeatherFetchLimits.read(limits.model_dump(mode="json"))
        self.credential, self.adapter_factory = credential, adapter_factory
        self.runtime = RuntimeSnapshot.capture()
        workspace.blobs.put(self.runtime.content)

    def parameters(self) -> Object:
        return {"kind": self.kind, "limits": {**self.limits.model_dump(mode="json")}}

    def execution_key(self) -> str:
        return execution_key(
            {
                "code_sha256": self.runtime.sha256,
                "models": dict(self.models),
                "parameters": self.parameters(),
            }
        )

    def context(self, inputs: Object) -> Context:
        plan = WeatherAcquisitionInputs.read(inputs.get("weather_acquisition")).plan(
            self.limits
        )
        return Context(
            self.runtime.sha256,
            dict(self.models),
            {
                "runtime_bundle": self.runtime.sha256,
                "weather_acquisition.plan": self.workspace.blobs.put_object(
                    plan.document()
                ),
            },
            self.parameters(),
        )

    def transport(self, limits: WeatherFetchLimits) -> ApifyTransport:
        return ApifyTransport(
            self.credential,
            limits,
            adapter=self.adapter_factory()
            if self.adapter_factory is not None
            else None,
        )

    def __call__(self, lease: Lease, control: Control) -> AssetResult:
        control.checkpoint()
        manifest_hash = lease.request.get("manifest_sha256")
        if not isinstance(manifest_hash, str):
            raise VersionUnavailable("weather task has no pinned manifest")
        manifest = frozen_manifest(self.workspace, lease, manifest_hash)
        if (
            request_execution_key(lease.request, manifest, manifest_hash)
            != self.execution_key()
        ):
            raise VersionUnavailable("worker cannot acquire the pinned weather source")
        context = manifest.get("context")
        assert isinstance(context, dict)
        pinned = context.get("assets")
        if (
            not isinstance(pinned, dict)
            or set(pinned) != {"runtime_bundle", "weather_acquisition.plan"}
            or any(not isinstance(value, str) for value in pinned.values())
            or pinned["runtime_bundle"] != self.runtime.sha256
        ):
            raise VersionUnavailable("exact weather runtime and plan required")
        self.workspace.blobs.read(str(pinned["runtime_bundle"]))
        plan = WeatherFetchPlan.from_document(
            self.workspace.blobs.object(str(pinned["weather_acquisition.plan"]))
        )
        inputs = self.workspace.pinned_inputs(manifest)
        expected = WeatherAcquisitionInputs.read(
            inputs.get("weather_acquisition")
        ).plan(self.limits)
        if encode(plan.document()) != encode(expected.document()):
            raise VersionUnavailable(
                "weather plan differs from its frozen project inputs"
            )
        journal = WeatherJournal(self.workspace)
        transport = self.transport(plan.limits)
        try:
            source = WeatherAcquisition(journal, ApifyWeatherClient(transport)).acquire(
                lease, plan, control
            )
        finally:
            transport.close()
        intent = journal.begin(lease, plan)
        if intent.capture_sha256 is None:
            raise VersionUnavailable("weather acquisition did not retain a capture")
        capture = self.workspace.blobs.object(intent.capture_sha256)
        dependencies = capture.get("dependencies")
        if not isinstance(dependencies, dict):
            raise VersionUnavailable("weather capture dependencies required")
        metadata: Object = {
            **weather_identity(source),
            "acquisition_limits": {**plan.limits.model_dump(mode="json")},
            "weather": weather_details(
                source,
                max_bytes=plan.limits.max_response_bytes,
                max_rows=plan.limits.max_weather_rows,
            ),
            "dependencies": {
                **dependencies,
                "weather_capture": intent.capture_sha256,
                "runtime_bundle": self.runtime.sha256,
            },
        }
        control.checkpoint()
        publication = AssetPublication.prepare(
            self.workspace.blobs,
            str(manifest["project_id"]),
            source.content,
            "application/json",
            WEATHER_PURPOSE,
            metadata,
        )
        return AssetResult(
            {
                "schema": 1,
                "kind": self.kind,
                "project_id": manifest["project_id"],
                "revision": manifest["revision"],
                "input_sha256": manifest["input_sha256"],
                "manifest_sha256": manifest_hash,
                "runtime_sha256": self.runtime.sha256,
                "pinned_assets": pinned,
                "weather_summary": metadata["weather"],
                "dependencies": metadata["dependencies"],
                "acquisition_run_id": intent.remote_run_id,
            },
            publication,
        )
