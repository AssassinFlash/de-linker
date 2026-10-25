"""Native durable shared-DC replay, bound to server-prepared Woo parameters."""

from __future__ import annotations

from collections.abc import Callable

from .assets import Asset
from .canonical import Json, Object, digest, encode
from .dc_battery_model import DcBatteryModel
from .dc_energy_output import flow_document, metrics
from .dc_energy_parameters import DcLossScenario, DcPreparedParameters
from .dc_energy_preparation import prepare_dc_energy
from .dc_parameter_source import confirm_dc_parameters
from .energy_equipment import assess_dc_energy_equipment
from .energy_kernel import EnergyKernel
from .equipment_inputs import EquipmentSelection
from .errors import EvidenceMissing, ProductEvidenceChanged, VersionUnavailable
from .frozen_profiles import frozen_profile
from .power_series import PowerSeries
from .pv_dc_profile import DcPvProfile, prepared_dc_profile
from .records import Actor, Context
from .shared_dc_checks import verify
from .shared_dc_dispatch import replay, self_consumption
from .worker import Control


class DcEnergyKernel(EnergyKernel):
    kind = "shared_dc_energy_replay_v1"
    coupling = "shared_dc"
    models = {
        "replay": kind,
        "battery": DcBatteryModel.version,
        "profiles": "retained_pv_dc_and_csv_ac_demand_v1",
        "controller": "self_consumption_shared_dc_v1",
        "source_accounting": "proportional_mixing_v1",
        "equipment_envelope": "selected_woo_dc_scenario_v1",
    }

    def context(self, actor: Actor, project_id: str, inputs: Object) -> Context:
        context = super().context(actor, project_id, inputs)
        if self.products is None or "woo.equipment_inputs" not in context.assets:
            raise EvidenceMissing(
                "woo_dc_parameters: current Woo equipment selection required"
            )
        parameters = DcPreparedParameters.read(
            self.workspace.blobs.object(
                context.assets["battery.dc_prepared_parameters"]
            )
        )
        confirm_dc_parameters(
            inputs,
            self.workspace.blobs.object(context.assets["woo.equipment_inputs"]),
            parameters,
        )
        confirm_dc_parameters(
            inputs,
            self.workspace.blobs.object(context.assets["battery.dc_woo_inputs"]),
            parameters,
        )
        if (
            any(period.mode == "outage" for period in self.scenario(inputs).schedule)
            and parameters.outage_bridge is None
        ):
            raise EvidenceMissing(
                "woo_dc_fact:backup_active_power",
                product_id=EquipmentSelection.read(
                    inputs.get("equipment_selection")
                ).inverter_product_id,
                fact_id="backup_ac_active_power_kw",
            )
        return context

    def parameter_dependencies(self, asset: Asset) -> dict[str, str]:
        assumptions = DcLossScenario.read(
            self.workspace.blobs.object(asset.content_sha256)
        )
        dependencies = asset.metadata.get("dependencies")
        if not isinstance(dependencies, dict) or set(dependencies) != {
            "dc_prepared_parameters",
            "dc_woo_inputs",
        }:
            raise EvidenceMissing(
                "woo_dc_parameters: server-prepared parameter dependencies required"
            )
        result: dict[str, str] = {}
        for name, sha in dependencies.items():
            if not isinstance(sha, str):
                raise VersionUnavailable("pinned DC parameter dependency hash required")
            self.workspace.blobs.read(sha)
            result[f"battery.{name}"] = sha
        prepared = DcPreparedParameters.read(
            self.workspace.blobs.object(result["battery.dc_prepared_parameters"])
        )
        if prepared.loss_scenario != assumptions:
            raise VersionUnavailable(
                "prepared DC parameters differ from their loss scenario"
            )
        return result

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
        if equipment_basis is None or self.products is None:
            raise EvidenceMissing(
                "woo_dc_parameters: selected current Woo equipment required"
            )
        parameters = DcPreparedParameters.read(
            self.workspace.blobs.object(dependency("battery.dc_prepared_parameters"))
        )
        confirm_dc_parameters(inputs, equipment_basis, parameters)
        confirm_dc_parameters(
            inputs,
            self.workspace.blobs.object(dependency("battery.dc_woo_inputs")),
            parameters,
        )
        if parameters.selection_sha256 != digest(
            encode(inputs.get("equipment_selection"))
        ):
            raise ProductEvidenceChanged(
                "DC parameters belong to another equipment selection"
            )
        profiles: dict[str, PowerSeries | DcPvProfile] = {}
        for role in scenario.profiles():
            if role == "pv_available_dc":
                assert scenario.pv_converter_id is not None
                profiles[role] = prepared_dc_profile(
                    self.workspace.blobs,
                    dependency(f"{role}.raw"),
                    self.workspace.blobs.object(dependency(f"{role}.metadata")),
                    scenario.pv_converter_id,
                )
            else:
                profiles[role] = frozen_profile(
                    self.workspace.blobs,
                    dependency(f"{role}.raw"),
                    dependency(f"{role}.metadata"),
                    dependency(f"{role}.timezone")
                    if f"{role}.timezone" in pinned
                    else None,
                )
        model = parameters.battery_model(dependency("battery.dc_prepared_parameters"))
        prepared = prepare_dc_energy(
            scenario, profiles, control, max_intervals=self.max_intervals
        )
        initial = scenario.initial_inventory.energy()
        flows = replay(
            prepared.frames,
            model,
            initial,
            self_consumption,
            checkpoint=control.checkpoint,
        )
        checked = verify(
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
        binding = assess_dc_energy_equipment(inputs, equipment_basis, model)
        return {
            "interval_count": len(flows),
            "scenario_constraint_status": "satisfied" if checked.passed else "violated",
            "verification": checked.document(),
            "metrics": metrics(flows, model),
            "model": model.document(),
            "battery_parameter_provenance": self.workspace.blobs.object(
                dependency("battery.metadata")
            ),
            "prepared_dc_parameters": parameters.model_dump(mode="json"),
            "profile_interpretation": prepared.profile_interpretation,
            "trace_sha256": trace_hash,
            "dependencies": {"energy_trace": trace_hash},
            "equipment_binding": binding,
        }
