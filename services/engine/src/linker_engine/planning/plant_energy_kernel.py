"""Durable joint-AC storage execution from one prepared Woo plant.

Each unit consumes its own source-derived, owned parameter asset. The
shared meter is the only grid boundary; a completed numerical replay does
not grant manufacturer joint-operation or country acceptance.
"""

from __future__ import annotations

from typing import cast

from .access import positive_integer
from .assets import Asset, Assets
from .canonical import Json, Object, encode
from .dc_energy_parameters import DcLossScenario, DcPreparedParameters
from .dc_parameter_source import confirm_dc_parameters
from .dc_plant_inputs import DcPlantEnergyInputs
from .energy_preparation import prepare_energy
from .equipment_candidate_choice import check_equipment_candidate
from .equipment_plant import EquipmentPlant
from .errors import EvidenceMissing, InvalidInput, NumericalFailure, VersionUnavailable
from .execution_identity import execution_key
from .frozen_profiles import frozen_profile
from .frozen_run import FrozenEnergyExecution, frozen_energy_execution
from .numerical_tolerance import Tolerance
from .plant_ac_parameters import storage_unit
from .plant_assessment import assess_plant, plant_products
from .plant_energy_checks import verify
from .plant_energy_dispatch import replay, self_consumption
from .plant_energy_inputs import PlantEnergyInputs
from .plant_energy_model import PlantFrame, StorageUnit
from .plant_energy_output import flow_document, metrics
from .product_sources import ProductSources
from .profile_assets import profile_dependencies
from .records import Actor, Context, Lease
from .runtime_snapshot import RuntimeSnapshot
from .worker import Control
from .workspace import Workspace

type PlantScenario = PlantEnergyInputs | DcPlantEnergyInputs


def check_plant_profile_boundary(
    scenario: PlantScenario, role: str, metadata: Object
) -> None:
    if (
        isinstance(scenario, DcPlantEnergyInputs)
        and role == "pv_available_ac"
        and scenario.pv_reference_asset_id is not None
        and metadata.get("profile_type")
        in {"pvlib_reference_profile_v1", "pvgis_roof_ac_reference_profile_v1"}
    ):
        # Both roof producers bind to this project's exact geometry. Imported
        # distinct external AC sources do not have either of these purposes.
        raise EvidenceMissing(
            "plant_dc_duplicate_pv_source: the whole roof AC profile would duplicate its retained PV groups",
            constraint_id="plant_dc_duplicate_pv_source",
        )


class PlantEnergyKernel:
    kind = "plant_ac_energy_replay_v1"
    models = {
        "replay": kind,
        "battery": "distinct_woo_battery_only_ac_equivalents_v1",
        "profiles": "csv_pvgis_and_geometry_bound_pv_reference_v2",
        "controller": "proportional_available_power_self_consumption_v1",
        "source_accounting": "proportional_mixing_per_unit_and_common_ac_bus_v1",
        "equipment_envelope": "selected_woo_plant_ac_scenario_v1",
    }

    def __init__(
        self,
        workspace: Workspace,
        tolerance: Tolerance,
        *,
        max_intervals: int,
        products: ProductSources,
    ) -> None:
        positive_integer(max_intervals, "maximum joint unit intervals")
        self.workspace, self.tolerance = workspace, tolerance
        self.max_intervals, self.products = max_intervals, products
        self.runtime = RuntimeSnapshot.capture()
        self.workspace.blobs.put(self.runtime.content)

    def parameters(self) -> Object:
        return {
            "kind": self.kind,
            "tolerance": self.tolerance.document(),
            "max_unit_intervals": self.max_intervals,
            "pv_boundary": "independent_ac_generation; each_storage_converter_dc_pv_explicitly_unused",
            "product_policy": "current_woo_plant_and_unit_parameter_assets_v1",
        }

    def execution_key(self) -> str:
        return execution_key(
            {
                "code_sha256": self.runtime.sha256,
                "models": dict(self.models),
                "parameters": self.parameters(),
            }
        )

    def scenario(self, inputs: Object) -> PlantScenario:
        return PlantEnergyInputs.from_project(inputs)

    @staticmethod
    def profile_bindings(scenario: PlantScenario) -> dict[str, tuple[str, str]]:
        result = {
            role: (role, asset_id) for role, asset_id in scenario.profiles().items()
        }
        if (
            isinstance(scenario, DcPlantEnergyInputs)
            and scenario.pv_reference_asset_id is not None
        ):
            result["pv_reference"] = ("pv_available_dc", scenario.pv_reference_asset_id)
        return result

    def validate_models(
        self, inputs: Object, scenario: PlantScenario, pinned: Object, basis: Object
    ) -> None:
        if not isinstance(scenario, PlantEnergyInputs):
            raise InvalidInput("an AC plant kernel requires its own scenario contract")
        self._models(inputs, scenario, pinned, basis)

    @staticmethod
    def unit_inputs(inputs: Object, plant: EquipmentPlant, unit_id: str) -> Object:
        unit = next((unit for unit in plant.units if unit.id == unit_id), None)
        if unit is None:
            raise InvalidInput("unknown prepared plant storage unit")
        result = {
            key: value
            for key, value in inputs.items()
            if key
            not in {
                "equipment_plant",
                "equipment_plant_setup",
                "equipment_plant_requirements",
                "equipment_candidate",
            }
        }
        result["equipment_selection"] = unit.selection.model_dump(mode="json")
        return result

    def parameter_dependencies(self, asset: Asset, unit_id: str) -> dict[str, str]:
        if (
            asset.purpose != "battery_parameters_v1"
            or asset.metadata.get("equipment_unit_id") != unit_id
        ):
            raise InvalidInput(
                "each plant unit needs its own server-prepared parameter asset"
            )
        assumptions = DcLossScenario.read(
            self.workspace.blobs.object(asset.content_sha256)
        )
        children = asset.metadata.get("dependencies")
        if (
            not isinstance(children, dict)
            or set(children) != {"dc_prepared_parameters", "dc_woo_inputs"}
            or any(not isinstance(v, str) for v in children.values())
        ):
            raise VersionUnavailable(
                "plant parameter asset has no source-bound dependencies"
            )
        result = cast(dict[str, str], children)
        prepared = DcPreparedParameters.read(
            self.workspace.blobs.object(result["dc_prepared_parameters"])
        )
        if assumptions != prepared.loss_scenario:
            raise VersionUnavailable(
                "plant parameter assumptions differ from their prepared proof"
            )
        self.workspace.blobs.read(result["dc_woo_inputs"])
        return result

    def _models(
        self, inputs: Object, scenario: PlantEnergyInputs, pinned: Object, basis: Object
    ) -> tuple[StorageUnit, ...]:
        plant = EquipmentPlant.from_inputs(inputs)
        plant_products(plant, basis)
        result = []
        for request in scenario.units:
            prefix = "unit:" + request.unit_id + ":battery."

            def dependency(name: str, prefix: str = prefix) -> str:
                value = pinned.get(prefix + name)
                if not isinstance(value, str):
                    raise VersionUnavailable(
                        "frozen plant parameter dependency missing"
                    )
                return value

            prepared = DcPreparedParameters.read(
                self.workspace.blobs.object(dependency("dc_prepared_parameters"))
            )
            selected = self.unit_inputs(inputs, plant, request.unit_id)
            confirm_dc_parameters(selected, basis, prepared)
            confirm_dc_parameters(
                selected,
                self.workspace.blobs.object(dependency("dc_woo_inputs")),
                prepared,
            )
            unit = storage_unit(
                request.unit_id, prepared, dependency("dc_prepared_parameters")
            )
            for period in scenario.schedule:
                unit.for_mode(period.mode)
            result.append(unit)
        return tuple(result)

    def context(self, actor: Actor, project_id: str, inputs: Object) -> Context:
        scenario = self.scenario(inputs)
        plant = EquipmentPlant.from_inputs(inputs)
        check_equipment_candidate(
            self.workspace, actor, project_id, inputs, previous=inputs
        )
        basis = self.products.equipment_basis()
        plant_products(plant, basis)
        assets = Assets(self.workspace)
        pinned = {
            "runtime_bundle": self.runtime.sha256,
            "woo.equipment_inputs": self.workspace.blobs.put_object(basis),
            "equipment.plant": self.workspace.blobs.put(
                encode(inputs["equipment_plant"])
            ),
        }
        for role, (measurement, asset_id) in self.profile_bindings(scenario).items():
            asset = assets.get(actor, project_id, asset_id)
            check_plant_profile_boundary(scenario, role, asset.metadata)
            self.products.check_profile(asset.metadata)
            pinned.update(
                profile_dependencies(
                    asset, measurement, inputs, self.workspace.blobs, binding=role
                )
            )
        for request in scenario.units:
            asset = assets.get(actor, project_id, request.battery_parameters_asset_id)
            prefix = "unit:" + request.unit_id + ":battery."
            pinned[prefix + "raw"], pinned[prefix + "metadata"] = (
                asset.content_sha256,
                asset.metadata_sha256,
            )
            pinned.update(
                {
                    prefix + name: sha
                    for name, sha in self.parameter_dependencies(
                        asset, request.unit_id
                    ).items()
                }
            )
        self.validate_models(inputs, scenario, cast(Object, pinned), basis)
        self.products.confirm_basis(basis, require_reference=False)
        return Context(
            self.runtime.sha256, dict(self.models), pinned, self.parameters()
        )

    def bind_assets(
        self,
        manifest: Object,
        inputs: Object,
        scenario: PlantScenario,
        pinned: Object,
    ) -> None:
        expected = {"runtime_bundle", "woo.equipment_inputs", "equipment.plant"}
        plant_hash = pinned.get("equipment.plant")
        if not isinstance(plant_hash, str) or self.workspace.blobs.object(
            plant_hash
        ) != inputs.get("equipment_plant"):
            raise VersionUnavailable("joint replay belongs to another prepared plant")
        profiles = self.profile_bindings(scenario)
        parameter_units = {
            "unit:" + unit.unit_id + ":battery": unit.unit_id for unit in scenario.units
        }
        references = {
            **{role: asset_id for role, (_, asset_id) in profiles.items()},
            **{
                "unit:" + unit.unit_id + ":battery": unit.battery_parameters_asset_id
                for unit in scenario.units
            },
        }
        with self.workspace.database.read() as connection:
            for role, asset_id in references.items():
                row = connection.execute(
                    "SELECT content_sha256, metadata_sha256, purpose, media_type FROM project_assets WHERE project_id=? AND id=?",
                    (manifest["project_id"], asset_id),
                ).fetchone()
                if (
                    row is None
                    or pinned.get(role + ".raw") != row["content_sha256"]
                    or pinned.get(role + ".metadata") != row["metadata_sha256"]
                ):
                    raise VersionUnavailable(
                        "joint dependency differs from its frozen owned asset"
                    )
                asset = Asset(
                    asset_id,
                    str(manifest["project_id"]),
                    row["content_sha256"],
                    row["media_type"],
                    row["purpose"],
                    row["metadata_sha256"],
                    self.workspace.blobs.object(row["metadata_sha256"]),
                )
                if role in parameter_units:
                    uid = parameter_units[role]
                    dependencies = {
                        role + ".raw": asset.content_sha256,
                        role + ".metadata": asset.metadata_sha256,
                        **{
                            role + "." + name: sha
                            for name, sha in self.parameter_dependencies(
                                asset, uid
                            ).items()
                        },
                    }
                else:
                    dependencies = profile_dependencies(
                        asset,
                        profiles[role][0],
                        inputs,
                        self.workspace.blobs,
                        binding=role,
                    )
                if any(pinned.get(name) != sha for name, sha in dependencies.items()):
                    raise VersionUnavailable("joint dependency proof changed")
                expected.update(dependencies)
        if set(pinned) != expected:
            raise VersionUnavailable(
                "joint dependency roles differ from the frozen scenario"
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
        inputs, pinned = execution.inputs, execution.pinned
        scenario = self.scenario(inputs)
        self.bind_assets(execution.manifest, inputs, scenario, pinned)
        basis = self.workspace.blobs.object(
            execution.dependency("woo.equipment_inputs")
        )
        self.products.confirm_basis(basis, require_reference=False)
        physical = self.calculate(execution, scenario, basis, control)
        control.checkpoint()
        self.products.confirm_basis(basis, require_reference=False)
        for role in self.profile_bindings(scenario):
            self.products.check_profile(
                self.workspace.blobs.object(execution.dependency(role + ".metadata"))
            )
        return execution.result(self.kind, physical)

    def calculate(
        self,
        execution: FrozenEnergyExecution,
        scenario: PlantScenario,
        basis: Object,
        control: Control,
    ) -> Object:
        if not isinstance(scenario, PlantEnergyInputs):
            raise InvalidInput("an AC plant kernel requires its own scenario contract")
        inputs, pinned = execution.inputs, execution.pinned
        units = self._models(inputs, scenario, pinned, basis)
        profiles = {}
        for role in scenario.profiles():
            self.products.check_profile(
                self.workspace.blobs.object(execution.dependency(role + ".metadata"))
            )
            profiles[role] = frozen_profile(
                self.workspace.blobs,
                execution.dependency(role + ".raw"),
                execution.dependency(role + ".metadata"),
                execution.dependency(role + ".timezone")
                if role + ".timezone" in pinned
                else None,
            )
        prepared = prepare_energy(
            scenario, profiles, control, max_intervals=self.max_intervals
        )
        if len(prepared.frames) * len(units) > self.max_intervals:
            raise InvalidInput(
                "joint device-interval count exceeds the configured execution budget"
            )
        reserves = {unit.unit_id: unit.reserve_kwh for unit in scenario.units}
        frames = tuple(PlantFrame(frame, reserves) for frame in prepared.frames)
        initial = {
            unit.unit_id: unit.initial_inventory.energy() for unit in scenario.units
        }
        flows = replay(
            frames,
            units,
            initial,
            self_consumption,
            checkpoint=control.checkpoint,
            tolerance=self.tolerance,
        )
        checked = verify(
            flows,
            units,
            self.tolerance,
            initial=initial,
            terminal_min_kwh={
                unit.unit_id: unit.terminal_min_kwh for unit in scenario.units
            },
        )
        if not checked.physical_passed:
            raise NumericalFailure(
                "joint replay failed its independent physical ledger checks"
            )
        trace: list[Json] = []
        for flow in flows:
            control.checkpoint()
            trace.append(flow_document(flow))
        trace_hash = self.workspace.blobs.put_object(
            {
                "schema": 1,
                "kind": self.kind,
                "manifest_sha256": execution.manifest_hash,
                "flows": trace,
            }
        )
        assessment = assess_plant(inputs, basis, control.checkpoint)
        parameter_pool: Object = {}
        parameter_units: list[Json] = []
        for request in scenario.units:
            prefix = "unit:" + request.unit_id + ":battery."
            sha = execution.dependency(prefix + "dc_prepared_parameters")
            parameter_pool.setdefault(sha, self.workspace.blobs.object(sha))
            metadata = self.workspace.blobs.object(
                execution.dependency(prefix + "metadata")
            )
            parameter_units.append(
                {
                    "unit_id": request.unit_id,
                    "parameter_sha256": sha,
                    "asset_id": request.battery_parameters_asset_id,
                    "provenance": metadata.get("provenance"),
                }
            )
        model = cast(
            Object,
            {
                "version": self.models["battery"],
                "pv_boundary": "independent_ac_generation; converter_dc_pv_inputs_unused",
                "source_accounting": self.models["source_accounting"],
                "units": [
                    {
                        "unit_id": unit.id,
                        "connected": unit.model.document(),
                        "outage": unit.outage_model.document()
                        if unit.outage_model
                        else None,
                    }
                    for unit in units
                ],
            },
        )
        physical: Object = {
            "interval_count": len(flows),
            "scenario_constraint_status": "satisfied" if checked.passed else "violated",
            "verification": checked.document(),
            "metrics": metrics(flows),
            "model": model,
            "profile_interpretation": prepared.profile_interpretation,
            "parameter_sources": {"units": parameter_units, "pool": parameter_pool},
            "trace_sha256": trace_hash,
            "dependencies": {"energy_trace": trace_hash},
            "equipment_binding": {
                "schema_version": 1,
                "model": self.models["equipment_envelope"],
                "plant": inputs["equipment_plant"],
                "plant_sha256": pinned["equipment.plant"],
                "scenario_model": model,
                "assessment": assessment,
                "performance_status": "not_established_by_scenario_envelope",
            },
        }
        return physical
