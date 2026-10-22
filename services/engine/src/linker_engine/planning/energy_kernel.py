"""The actual version-pinned CSV-to-continuous-energy durable job handler.

This handler does physical replay. It is not an equipment/country release or
the whole planner: those assessments compose with this same frozen run later.
It reads pinned dependencies only; no network, OS timezone or latest-product
lookup occurs during execution.
"""

from __future__ import annotations

from .access import positive_integer
from .assets import Assets
from .battery_model import BatteryModel
from .canonical import Json, Object
from .dispatch import replay, self_consumption_with_reserve
from .dispatch_checks import verify
from .energy_inputs import BatteryParameters, EnergyInputs
from .energy_metrics import metrics
from .energy_preparation import prepare_energy
from .errors import InvalidInput, VersionUnavailable
from .flow_document import flow_document
from .frozen_profiles import frozen_profile
from .frozen_run import bind_energy_assets, frozen_manifest
from .numerical_tolerance import Tolerance
from .records import Actor, Context, Lease
from .runtime_snapshot import RuntimeSnapshot
from .worker import Control
from .workspace import Workspace


class EnergyKernel:
    kind = "single_ac_energy_replay_v1"
    models = {
        "replay": kind,
        "battery": BatteryModel.version,
        "profiles": "csv_interval_means_v1",
        "controller": "self_consumption_with_reserve_v1",
        "source_accounting": "proportional_mixing_v1",
    }

    def __init__(
        self, workspace: Workspace, tolerance: Tolerance, *, max_intervals: int
    ) -> None:
        positive_integer(max_intervals, "maximum aligned intervals")
        self.workspace = workspace
        self.tolerance = tolerance
        self.max_intervals = max_intervals
        self.runtime = RuntimeSnapshot.capture()
        self.workspace.blobs.put(self.runtime.content)

    def context(self, actor: Actor, project_id: str, scenario: EnergyInputs) -> Context:
        assets = Assets(self.workspace)
        pinned: dict[str, str] = {"runtime_bundle": self.runtime.sha256}
        for role, asset_id in scenario.profiles().items():
            asset = assets.get(actor, project_id, asset_id)
            if asset.purpose != "csv_profile_v1":
                raise InvalidInput(f"{role}: an imported profile asset is required")
            timezone_hash = asset.metadata.get("timezone_rules_sha256")
            if not isinstance(timezone_hash, str):
                raise VersionUnavailable("profile has no pinned timezone rules")
            pinned[f"{role}.raw"] = asset.content_sha256
            pinned[f"{role}.metadata"] = asset.metadata_sha256
            pinned[f"{role}.timezone"] = timezone_hash
        battery = assets.get(actor, project_id, scenario.battery_parameters_asset_id)
        if battery.purpose != "battery_parameters_v1":
            raise InvalidInput("explicit battery-parameter asset is required")
        BatteryParameters.read(self.workspace.blobs.object(battery.content_sha256))
        pinned["battery.raw"] = battery.content_sha256
        pinned["battery.metadata"] = battery.metadata_sha256
        return Context(
            self.runtime.sha256,
            dict(self.models),
            pinned,
            {
                "kind": self.kind,
                "tolerance": self.tolerance.document(),
                "max_intervals": self.max_intervals,
            },
        )

    def __call__(self, lease: Lease, control: Control) -> Object:
        control.checkpoint()
        manifest_hash = lease.request.get("manifest_sha256")
        if not isinstance(manifest_hash, str):
            raise VersionUnavailable("evaluation has no pinned manifest")
        manifest = frozen_manifest(self.workspace, lease, manifest_hash)
        context = manifest.get("context")
        if (
            not isinstance(context, dict)
            or context.get("code_sha256") != self.runtime.sha256
            or context.get("models") != self.models
        ):
            raise VersionUnavailable(
                "this worker cannot execute the pinned runtime/models"
            )
        parameters = context.get("parameters")
        expected_parameters = {
            "kind": self.kind,
            "tolerance": self.tolerance.document(),
            "max_intervals": self.max_intervals,
        }
        if parameters != expected_parameters:
            raise VersionUnavailable(
                "this worker cannot execute the pinned numerical settings"
            )
        pinned = context.get("assets")
        if not isinstance(pinned, dict) or any(
            not isinstance(value, str) for value in pinned.values()
        ):
            raise VersionUnavailable("pinned dependency hashes required")

        def dependency(name: str) -> str:
            value = pinned.get(name)
            if not isinstance(value, str):
                raise VersionUnavailable(f"pinned dependency missing: {name}")
            self.workspace.blobs.read(value)
            return value

        if dependency("runtime_bundle") != self.runtime.sha256:
            raise VersionUnavailable("runtime bundle and code identity differ")
        inputs = self.workspace.pinned_inputs(manifest)
        scenario = EnergyInputs.from_project(inputs)
        bind_energy_assets(self.workspace, manifest, scenario, pinned)
        profiles = {
            role: frozen_profile(
                self.workspace.blobs,
                dependency(f"{role}.raw"),
                dependency(f"{role}.metadata"),
                dependency(f"{role}.timezone"),
            )
            for role in scenario.profiles()
        }
        parameter_hash = dependency("battery.raw")
        parameter_metadata = self.workspace.blobs.object(dependency("battery.metadata"))
        model = BatteryParameters.read(
            self.workspace.blobs.object(parameter_hash)
        ).battery(parameter_hash)
        prepared = prepare_energy(
            scenario, profiles, control, max_intervals=self.max_intervals
        )
        initial = scenario.initial_inventory.energy()
        flows = replay(
            prepared.frames,
            model,
            initial,
            self_consumption_with_reserve,
            checkpoint=control.checkpoint,
            tolerance=self.tolerance,
        )
        verification = verify(
            flows,
            model,
            self.tolerance,
            initial=initial,
            terminal_min_kwh=scenario.terminal_min_kwh,
        )
        trace: list[Json] = []
        for flow in flows:
            control.checkpoint()
            trace.append(flow_document(flow))
        trace_hash = self.workspace.blobs.put_object(
            {
                "schema": 1,
                "kind": self.kind,
                "manifest_sha256": manifest_hash,
                "flows": trace,
            }
        )
        control.checkpoint()
        return {
            "schema": 1,
            "kind": self.kind,
            "project_id": manifest.get("project_id"),
            "revision": manifest.get("revision"),
            "input_sha256": manifest.get("input_sha256"),
            "manifest_sha256": manifest_hash,
            "runtime_sha256": self.runtime.sha256,
            "interval_count": len(flows),
            "scenario_constraint_status": "satisfied"
            if verification.passed
            else "violated",
            "verification": verification.document(),
            "metrics": metrics(flows, model),
            "model": model.document(),
            "battery_parameter_provenance": parameter_metadata,
            "profile_interpretation": prepared.profile_interpretation,
            "pinned_assets": pinned,
            "trace_sha256": trace_hash,
            "dependencies": {"energy_trace": trace_hash},
            "equipment_release": {
                "status": "not_assessed",
                "reason": "explicit_scenario_replay_is_not_equipment_release",
            },
            "country_assessment": {
                "status": "not_assessed",
                "reason": "country_rules_are_a_separate_assessment",
            },
        }
