"""The actual version-pinned CSV-to-continuous-energy durable job handler.

This handler does physical replay. It is not an equipment/country release or
the whole planner: those assessments compose with this same frozen run later.
Physical replay reads pinned inputs only. A configured source guard checks
current Woo permission around the replay without substituting product facts.
"""

from __future__ import annotations

from collections.abc import Callable

from .access import positive_integer
from .assets import Asset, Assets
from .battery_model import BatteryModel
from .canonical import Json, Object, encode
from .dispatch import replay, self_consumption_with_reserve
from .dispatch_checks import verify
from .energy_equipment import MODEL as EQUIPMENT_MODEL
from .energy_equipment import assess_energy_equipment
from .energy_inputs import BatteryParameters, EnergyInputs
from .energy_metrics import metrics
from .energy_preparation import prepare_energy
from .equipment_assessment import selection_products
from .equipment_candidate_choice import check_equipment_candidate
from .equipment_inputs import EquipmentSelection
from .errors import InvalidInput, VersionUnavailable
from .execution_identity import execution_key
from .flow_document import flow_document
from .frozen_profiles import frozen_profile
from .frozen_run import bind_energy_assets, frozen_energy_execution
from .numerical_tolerance import Tolerance
from .product_sources import ProductSources
from .profile_assets import profile_dependencies
from .records import Actor, Context, Lease
from .worker import Control
from .workspace import Workspace


class EnergyKernel:
    kind = "single_ac_energy_replay_v1"
    coupling = "independent_ac"
    models = {
        "replay": kind,
        "battery": BatteryModel.version,
        "profiles": "csv_pvgis_and_geometry_bound_pv_reference_v2",
        "controller": "self_consumption_with_reserve_v1",
        "source_accounting": "proportional_mixing_v1",
        "equipment_envelope": EQUIPMENT_MODEL,
    }

    def __init__(
        self,
        workspace: Workspace,
        tolerance: Tolerance,
        *,
        max_intervals: int,
        products: ProductSources | None = None,
    ) -> None:
        positive_integer(max_intervals, "maximum aligned intervals")
        self.workspace = workspace
        self.tolerance = tolerance
        self.max_intervals = max_intervals
        self.products = products
        self.runtime = self.workspace.kernel_runtime()

    def parameters(self) -> Object:
        return {
            "kind": self.kind,
            "tolerance": self.tolerance.document(),
            "max_intervals": self.max_intervals,
            "product_policy": "current_woo_profile_and_selected_equipment_v2"
            if self.products
            else "isolated_algorithm_fixture",
        }

    def execution_key(self) -> str:
        return execution_key(
            {
                "code_sha256": self.runtime.sha256,
                "models": dict(self.models),
                "parameters": self.parameters(),
            }
        )

    def context(self, actor: Actor, project_id: str, inputs: Object) -> Context:
        scenario = self.scenario(inputs)
        assets = Assets(self.workspace)
        pinned: dict[str, str] = {"runtime_bundle": self.runtime.sha256}
        for role, asset_id in scenario.profiles().items():
            asset = assets.get(actor, project_id, asset_id)
            if self.products is not None:
                self.products.check_profile(asset.metadata)
            pinned.update(
                profile_dependencies(asset, role, inputs, self.workspace.blobs)
            )
        battery = assets.get(actor, project_id, scenario.battery_parameters_asset_id)
        if battery.purpose != "battery_parameters_v1":
            raise InvalidInput("explicit battery-parameter asset is required")
        pinned.update(self.parameter_dependencies(battery))
        pinned["battery.raw"] = battery.content_sha256
        pinned["battery.metadata"] = battery.metadata_sha256
        if "equipment_selection" in inputs:
            if self.products is None:
                raise InvalidInput("selected equipment requires the current Woo source")
            check_equipment_candidate(
                self.workspace, actor, project_id, inputs, previous=inputs
            )
            basis = self.products.equipment_basis()
            selection_products(
                EquipmentSelection.read(inputs["equipment_selection"]), basis
            )
            pinned["woo.equipment_inputs"] = self.workspace.blobs.put_object(basis)
            pinned["equipment.selection"] = self.workspace.blobs.put(
                encode(inputs["equipment_selection"])
            )
        return Context(
            self.runtime.sha256,
            dict(self.models),
            pinned,
            self.parameters(),
        )

    def __call__(self, lease: Lease, control: Control) -> Object:
        control.checkpoint()
        execution = frozen_energy_execution(
            self.workspace,
            lease,
            runtime_sha256=self.runtime.sha256,
            models=self.models,
            parameters=self.parameters(),
        )
        manifest_hash, manifest = execution.manifest_hash, execution.manifest
        inputs, pinned = execution.inputs, execution.pinned
        dependency = execution.dependency
        scenario = self.scenario(inputs)
        bind_energy_assets(self.workspace, manifest, scenario, inputs, pinned)
        equipment_basis = (
            self.workspace.blobs.object(dependency("woo.equipment_inputs"))
            if "equipment_selection" in inputs
            else None
        )
        if equipment_basis is not None:
            if self.products is None:
                raise VersionUnavailable("current Woo equipment source is unavailable")
            self.products.confirm_basis(equipment_basis, require_reference=False)
        if self.products is not None:
            for role in scenario.profiles():
                self.products.check_profile(
                    self.workspace.blobs.object(dependency(f"{role}.metadata"))
                )
        physical = self.calculate(
            inputs, pinned, manifest_hash, equipment_basis, dependency, control
        )
        control.checkpoint()
        if self.products is not None:
            for role in scenario.profiles():
                self.products.check_profile(
                    self.workspace.blobs.object(dependency(f"{role}.metadata"))
                )
            if equipment_basis is not None:
                self.products.confirm_basis(equipment_basis, require_reference=False)
        return execution.result(self.kind, physical)

    def scenario(self, inputs: Object) -> EnergyInputs:
        scenario = EnergyInputs.from_project(inputs)
        if scenario.coupling != self.coupling:
            raise InvalidInput(
                "energy coupling differs from the selected physical executor"
            )
        return scenario

    def validate_parameter_document(self, value: Object) -> None:
        BatteryParameters.read(value)

    def parameter_dependencies(self, asset: Asset) -> dict[str, str]:
        self.validate_parameter_document(
            self.workspace.blobs.object(asset.content_sha256)
        )
        return {}

    def calculate(
        self,
        inputs: Object,
        pinned: Object,
        manifest_hash: str,
        equipment_basis: Object | None,
        dependency: Callable[[str], str],
        control: Control,
    ) -> Object:
        scenario = self.scenario(inputs)
        profiles = {
            role: frozen_profile(
                self.workspace.blobs,
                dependency(f"{role}.raw"),
                dependency(f"{role}.metadata"),
                dependency(f"{role}.timezone")
                if f"{role}.timezone" in pinned
                else None,
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
        equipment_binding = (
            assess_energy_equipment(inputs, equipment_basis, model)
            if equipment_basis is not None
            else None
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
        return {
            "interval_count": len(flows),
            "scenario_constraint_status": "satisfied"
            if verification.passed
            else "violated",
            "verification": verification.document(),
            "metrics": metrics(flows, model),
            "model": model.document(),
            "battery_parameter_provenance": parameter_metadata,
            "profile_interpretation": prepared.profile_interpretation,
            "trace_sha256": trace_hash,
            "dependencies": {"energy_trace": trace_hash},
            "equipment_binding": equipment_binding,
        }
