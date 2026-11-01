"""Distinct durable official calendar-year roof AC reference producer."""

import time
from collections.abc import Callable
from typing import cast

from .asset_publication import AssetResult
from .canonical import Object, encode
from .errors import VersionUnavailable
from .execution_identity import execution_key, request_execution_key
from .frozen_run import frozen_manifest
from .product_sources import ProductSources
from .pvgis_reference_artifacts import prepare_reference_asset
from .pvgis_reference_download import ReferenceCapture, ReferenceDownloader
from .pvgis_reference_geometry import reference_plan
from .pvgis_reference_journal import PvgisReferenceJournal
from .pvgis_reference_plan import PvgisReferencePlan
from .pvgis_reference_transport import PvgisReferenceTransport
from .records import Context, Lease
from .weather_fetch_errors import WeatherResponseTooLarge
from .weather_fetch_plan import WeatherFetchLimits
from .weather_journal import WeatherDeadlineExceeded
from .weather_task import WeatherTask
from .worker import Control
from .workspace import Workspace


class PvgisRoofReferenceKernel:
    kind = "prepare_pvgis_roof_ac_reference_v1"
    models = {
        "task": kind,
        "generation": "pvgis_5_3_roof_ac_reference_v1",
        "acquisition": "official_jrc_https_get_original_v1",
        "aggregate": "exact_same_axis_array_ac_sum_v1",
    }

    def __init__(
        self,
        workspace: Workspace,
        products: ProductSources,
        limits: WeatherFetchLimits,
        *,
        max_array_steps: int,
        transport_factory: Callable[[], ReferenceDownloader] | None = None,
    ) -> None:
        self.workspace, self.products = workspace, products
        self.limits = WeatherFetchLimits.read(limits.model_dump(mode="json"))
        if type(max_array_steps) is not int or max_array_steps <= 0:
            raise ValueError("positive deployment array/hour resource budget required")
        self.max_array_steps = max_array_steps
        self.transport_factory = transport_factory
        self.runtime = workspace.kernel_runtime()

    def parameters(self) -> Object:
        return {
            "kind": self.kind,
            "limits": self.limits.model_dump(mode="json"),
            "max_array_steps": self.max_array_steps,
            "retained_original_bytes_policy": "shared_complete_originals_and_remaining_response_cap",
            "product_policy": "current_woo_included_roof_module_v1",
        }

    def execution_key(self) -> str:
        return execution_key(
            {
                "code_sha256": self.runtime.sha256,
                "models": dict(self.models),
                "parameters": self.parameters(),
            }
        )

    def context(self, inputs: Object) -> Context:
        basis = self.products.roof_basis(inputs)
        basis_sha = self.workspace.blobs.put_object(basis)
        plan = reference_plan(inputs, basis_sha, self.limits, self.max_array_steps)
        return Context(
            self.runtime.sha256,
            dict(self.models),
            {
                "runtime_bundle": self.runtime.sha256,
                "woo.module_inputs": basis_sha,
                "pvgis_reference.plan": self.workspace.blobs.put_object(
                    plan.document()
                ),
            },
            self.parameters(),
        )

    def __call__(self, lease: Lease, control: Control) -> AssetResult:
        control.checkpoint()
        manifest_hash = lease.request.get("manifest_sha256")
        if not isinstance(manifest_hash, str):
            raise VersionUnavailable("roof reference task has no pinned manifest")
        manifest = frozen_manifest(self.workspace, lease, manifest_hash)
        if (
            request_execution_key(lease.request, manifest, manifest_hash)
            != self.execution_key()
        ):
            raise VersionUnavailable("worker cannot execute the pinned roof reference")
        context = manifest.get("context")
        assert isinstance(context, dict)
        pinned = context.get("assets")
        if (
            not isinstance(pinned, dict)
            or set(pinned)
            != {"runtime_bundle", "woo.module_inputs", "pvgis_reference.plan"}
            or any(not isinstance(v, str) for v in pinned.values())
            or pinned["runtime_bundle"] != self.runtime.sha256
        ):
            raise VersionUnavailable(
                "exact roof reference runtime and dependencies required"
            )
        self.workspace.blobs.read(str(pinned["runtime_bundle"]))
        basis = self.workspace.blobs.object(str(pinned["woo.module_inputs"]))
        self.products.confirm_basis(basis)
        inputs = self.workspace.pinned_inputs(manifest)
        self.products.check_roof_inputs(inputs, basis)
        plan = PvgisReferencePlan.read(
            self.workspace.blobs.object(str(pinned["pvgis_reference.plan"]))
        )
        expected = reference_plan(
            inputs, str(pinned["woo.module_inputs"]), self.limits, self.max_array_steps
        )
        if encode(plan.document()) != encode(expected.document()):
            raise VersionUnavailable(
                "roof reference plan differs from the saved project"
            )
        journal = PvgisReferenceJournal(self.workspace, lease, plan)
        acquisition = journal.begin()
        deadline = cast(float, acquisition["deadline_at"])
        task = WeatherTask(self.workspace, lease, control, deadline)
        remaining_time = min(
            deadline - self.workspace.clock(), self.limits.max_elapsed_seconds
        )
        monotonic_deadline = time.monotonic() + remaining_time

        def guard() -> None:
            task.check()
            if (
                self.workspace.clock() < cast(float, acquisition["started_at"])
                or time.monotonic() >= monotonic_deadline
            ):
                raise WeatherDeadlineExceeded("roof reference original deadline passed")

        transport = (
            self.transport_factory()
            if self.transport_factory
            else PvgisReferenceTransport()
        )
        captures: list[ReferenceCapture] = []
        try:
            for index, array in enumerate(plan.arrays):
                guard()
                source = journal.captured(index)
                if source is None:
                    state = journal.current()
                    remaining_bytes = self.limits.max_response_bytes - cast(
                        int, state["consumed_bytes"]
                    )
                    if remaining_bytes <= 0:
                        raise WeatherResponseTooLarge(
                            "roof reference shared byte budget exhausted"
                        )
                    transfer_limits = WeatherFetchLimits.read(
                        {
                            **self.limits.model_dump(mode="json"),
                            "max_response_bytes": remaining_bytes,
                            "max_metadata_bytes": min(
                                self.limits.max_metadata_bytes, remaining_bytes
                            ),
                        }
                    )
                    source = transport.download(
                        array.request,
                        transfer_limits,
                        deadline=deadline,
                        clock=self.workspace.clock,
                        guard=guard,
                    )
                    journal.retain(index, source)
                guard()
                journal.validate(index, source)
                captures.append(source)
        finally:
            transport.close()
        guard()
        publication, summary = prepare_reference_asset(
            self.workspace.blobs,
            str(manifest["project_id"]),
            int(str(manifest["revision"])),
            inputs,
            basis,
            plan,
            captures,
            guard=guard,
            acquisition=journal.current(),
        )
        guard()
        self.products.confirm_basis(basis)
        metadata = self.workspace.blobs.object(publication.metadata_sha256)
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
                "profile_summary": summary,
                "dependencies": metadata["dependencies"],
                "equipment_release": {"status": "not_assessed"},
                "country_assessment": {"status": "not_assessed"},
                "near_shading_assessment": {"status": "not_assessed"},
            },
            publication,
        )
