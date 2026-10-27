"""Owned, frozen multi-hybrid execution using the same physical DC ports."""

from __future__ import annotations

import math
from typing import cast

from .canonical import Json, Object
from .dc_energy_parameters import DcPreparedParameters
from .dc_parameter_source import confirm_dc_parameters
from .dc_plant_checks import verify
from .dc_plant_dispatch import replay
from .dc_plant_inputs import DcPlantEnergyInputs
from .dc_plant_model import DcPlantUnit
from .dc_plant_output import flow_document, metrics
from .dc_plant_preparation import prepare
from .equipment_plant import EquipmentPlant
from .errors import EvidenceMissing, InvalidInput, NumericalFailure, VersionUnavailable
from .frozen_profiles import frozen_profile
from .frozen_run import FrozenEnergyExecution
from .plant_assessment import assess_plant, plant_products
from .plant_energy_kernel import PlantEnergyKernel, PlantScenario
from .plant_pv_profiles import PlantPvProfiles, project
from .pv_profile_artifacts import model_dependencies
from .worker import Control


class DcPlantEnergyKernel(PlantEnergyKernel):
    kind = "plant_shared_dc_energy_replay_v1"
    models = {
        "replay": kind,
        "battery": "distinct_woo_shared_dc_ports_v1",
        "profiles": "retained_partitioned_dc_ac_pv_and_csv_demand_v1",
        "controller": "local_dc_then_proportional_ac_self_consumption_v1",
        "source_accounting": "proportional_mixing_per_unit_and_common_ac_bus_v1",
        "equipment_envelope": "selected_woo_plant_dc_scenario_v1",
    }

    def parameters(self) -> Object:
        return {
            "kind": self.kind,
            "tolerance": self.tolerance.document(),
            "max_unit_intervals": self.max_intervals,
            "pv_boundary": "each_retained_group_assigned_once_at_its_DC_or_AC_stage",
            "product_policy": "current_woo_plant_and_unit_parameter_assets_v1",
        }

    def scenario(self, inputs: Object) -> DcPlantEnergyInputs:
        return DcPlantEnergyInputs.from_project(inputs)

    def _dc_models(
        self,
        inputs: Object,
        scenario: DcPlantEnergyInputs,
        pinned: Object,
        basis: Object,
    ) -> tuple[DcPlantUnit, ...]:
        plant = EquipmentPlant.from_inputs(inputs)
        plant_products(plant, basis)
        result = []
        for request in scenario.units:
            prefix = "unit:" + request.unit_id + ":battery."
            sha, woo = (
                pinned.get(prefix + "dc_prepared_parameters"),
                pinned.get(prefix + "dc_woo_inputs"),
            )
            if not isinstance(sha, str) or not isinstance(woo, str):
                raise VersionUnavailable(
                    "each frozen DC port needs its own source proof"
                )
            parameters = DcPreparedParameters.read(self.workspace.blobs.object(sha))
            selected = self.unit_inputs(inputs, plant, request.unit_id)
            confirm_dc_parameters(selected, basis, parameters)
            confirm_dc_parameters(
                selected, self.workspace.blobs.object(woo), parameters
            )
            model = parameters.battery_model(sha)
            for period in scenario.schedule:
                model.bridge(period.mode)
            result.append(DcPlantUnit(request.unit_id, model, request.allow_ac_charge))
        return tuple(result)

    def validate_models(
        self, inputs: Object, scenario: PlantScenario, pinned: Object, basis: Object
    ) -> None:
        if not isinstance(scenario, DcPlantEnergyInputs):
            raise InvalidInput("the DC plant executor requires its own scenario")
        self._dc_models(inputs, scenario, pinned, basis)

    def _pv(
        self, execution: FrozenEnergyExecution, scenario: DcPlantEnergyInputs
    ) -> PlantPvProfiles:
        if scenario.pv_reference_asset_id is None:
            return PlantPvProfiles({}, None)
        metadata = self.workspace.blobs.object(
            execution.dependency("pv_reference.metadata")
        )
        result = project(
            self.workspace.blobs,
            execution.dependency("pv_reference.raw"),
            metadata,
            scenario,
        )
        witness = self.workspace.blobs.object(
            model_dependencies(metadata)["pv_model_witness"]
        )
        arrays = witness.get("arrays")
        if not isinstance(arrays, list):
            raise VersionUnavailable("PV array nameplate witnesses are missing")
        array_power = {}
        for row in arrays:
            if (
                not isinstance(row, dict)
                or not isinstance(row.get("id"), str)
                or type(row.get("stc_power_w")) not in (float, int)
            ):
                raise VersionUnavailable("PV array nameplate witness is invalid")
            array_power[row["id"]] = float(cast(float, row["stc_power_w"]))
        selections = {
            u.id: u.selection
            for u in EquipmentPlant.from_inputs(execution.inputs).units
        }
        for uid, pv in result.dc.items():
            actual = math.fsum(array_power[array] for array in pv.array_ids) / 1000
            declared = selections[uid].pv_dc_kw
            if declared is None:
                raise InvalidInput(
                    "each converter requires an explicit DC PV nameplate allocation"
                )
            # Representation rounding only; this is not a hardware/design margin.
            if abs(actual - declared) > math.fsum(
                (math.ulp(actual), math.ulp(declared))
            ):
                raise EvidenceMissing(
                    "plant_dc_pv_nameplate_mismatch: the assigned PV group's STC power differs from its unit's declared DC PV allocation",
                    constraint_id="plant_dc_pv_nameplate_mismatch",
                )
        return result

    def calculate(
        self,
        execution: FrozenEnergyExecution,
        scenario: PlantScenario,
        basis: Object,
        control: Control,
    ) -> Object:
        if not isinstance(scenario, DcPlantEnergyInputs):
            raise InvalidInput("the DC plant executor requires its own scenario")
        units = self._dc_models(execution.inputs, scenario, execution.pinned, basis)
        profiles = {}
        for role in scenario.profiles():
            metadata = self.workspace.blobs.object(
                execution.dependency(role + ".metadata")
            )
            self.products.check_profile(metadata)
            if (
                role == "pv_available_ac"
                and scenario.pv_reference_asset_id is not None
                and metadata.get("profile_type") == "pvlib_reference_profile_v1"
            ):
                raise InvalidInput(
                    "assign the roof reference's AC groups explicitly; its total AC output would duplicate the DC groups"
                )
            profiles[role] = frozen_profile(
                self.workspace.blobs,
                execution.dependency(role + ".raw"),
                execution.dependency(role + ".metadata"),
                execution.dependency(role + ".timezone")
                if role + ".timezone" in execution.pinned
                else None,
            )
        pv = self._pv(execution, scenario)
        prepared = prepare(
            scenario, profiles, pv.dc, pv.ac, control, max_intervals=self.max_intervals
        )
        initial = {u.unit_id: u.initial_inventory.energy() for u in scenario.units}
        flows = replay(prepared.frames, units, initial, checkpoint=control.checkpoint)
        checked = verify(
            flows,
            units,
            self.tolerance,
            initial=initial,
            terminal_min_kwh={u.unit_id: u.terminal_min_kwh for u in scenario.units},
        )
        if not checked.physical_passed:
            raise NumericalFailure(
                "DC plant replay failed an independent port, source or common-meter witness"
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
        pool: Object = {}
        parameter_units: list[Json] = []
        for request in scenario.units:
            prefix = "unit:" + request.unit_id + ":battery."
            sha = execution.dependency(prefix + "dc_prepared_parameters")
            pool.setdefault(sha, self.workspace.blobs.object(sha))
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
        assignments = {u.unit_id: u.pv_converter_id for u in scenario.units}
        model = cast(
            Object,
            {
                "version": self.models["battery"],
                "source_accounting": self.models["source_accounting"],
                "pv_boundary": "each_retained_group_assigned_once_at_its_DC_or_AC_stage",
                "ac_pv_converter_ids": list(scenario.ac_pv_converter_ids),
                "units": [
                    {
                        "unit_id": u.id,
                        "dc_model": u.model.document(),
                        "pv_converter_id": assignments[u.id],
                        "allow_ac_charge": u.allow_ac_charge,
                    }
                    for u in units
                ],
            },
        )
        return {
            "interval_count": len(flows),
            "scenario_constraint_status": "satisfied" if checked.passed else "violated",
            "verification": checked.document(),
            "metrics": metrics(flows),
            "model": model,
            "profile_interpretation": prepared.profile_interpretation,
            "parameter_sources": {"units": parameter_units, "pool": pool},
            "trace_sha256": trace_hash,
            "dependencies": {"energy_trace": trace_hash},
            "equipment_binding": {
                "schema_version": 1,
                "model": self.models["equipment_envelope"],
                "plant": execution.inputs["equipment_plant"],
                "plant_sha256": execution.pinned["equipment.plant"],
                "scenario_model": model,
                "assessment": assess_plant(execution.inputs, basis, control.checkpoint),
                "performance_status": "not_established_by_scenario_envelope",
            },
        }
