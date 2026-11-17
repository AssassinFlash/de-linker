"""Compile current authored declarations; execution projections belong to a run."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from uuid import uuid4

from .asset_validation import validate_asset
from .assets import Asset, Assets
from .canonical import Json, Object, decode_object, encode
from .dc_energy_parameters import DcLossScenario
from .dc_parameter_source import prepare_dc_parameters
from .energy_inputs import BatteryParameters, InitialInventory, storage_only_project
from .equipment_plant import EquipmentPlant
from .errors import InvalidInput
from .interval import Interval, utc
from .plant_energy_kernel import PlantEnergyKernel
from .product_sources import ProductSources
from .profile_selections import ProfileSelections, check_profile_selections
from .records import Actor
from .workspace import Workspace


def object_value(value: Json, name: str) -> Object:
    if not isinstance(value, dict):
        raise InvalidInput(f"{name} requires an object")
    return value


def normalize_authored_inputs(inputs: Object) -> Object:
    """Drop only the execution projections this command owns."""
    result = decode_object(encode(inputs))
    result.pop("energy_replay", None)
    result.pop("energy_plant", None)
    scenario = result.get("energy_scenario")
    if isinstance(scenario, dict):
        scenario.pop("battery_binding", None)
    plant = result.get("energy_plant_setup")
    if isinstance(plant, dict):
        units = plant.get("units")
        if isinstance(units, list):
            for unit in units:
                settings = unit.get("settings") if isinstance(unit, dict) else None
                if isinstance(settings, dict):
                    settings.pop("battery_binding", None)
    return result


def schedule(
    periods: Json, *, storage_only: bool, plant: bool = False, no_storage: bool = False
) -> list[Json]:
    if not isinstance(periods, list) or not periods:
        raise InvalidInput("explicit operating periods required")
    result: list[Json] = []
    for index, raw in enumerate(periods):
        period = object_value(raw, "operating period")
        path = (
            "energy_plant_setup" if plant else "energy_scenario"
        ) + f".schedule[{index}]"
        instants: dict[str, datetime] = {}
        invalid_fields = []
        for field in ("start_utc", "end_utc"):
            value = period.get(field)
            if not isinstance(value, str):
                invalid_fields.append(path + "." + field)
                continue
            try:
                instants[field] = utc(datetime.fromisoformat(value))
            except (ValueError, InvalidInput):
                invalid_fields.append(path + "." + field)
        if invalid_fields:
            raise InvalidInput(
                "operating periods require explicit ISO timestamps",
                fields=invalid_fields,
            )
        try:
            Interval(instants["start_utc"], instants["end_utc"])
        except InvalidInput as error:
            raise InvalidInput(
                "operating period end must follow its start",
                fields=(path + ".start_utc", path + ".end_utc"),
            ) from error
        outage = period.get("mode") == "outage"
        if outage and period.get("allow_grid_charge") is True:
            raise InvalidInput("grid charging cannot be enabled during an outage")
        limits: Object = {}
        for direction in ("import", "export"):
            policy, cap = (
                period.get(direction + "_policy"),
                period.get(direction + "_cap_kw"),
            )
            if not outage and (
                policy not in ("unlimited", "limited")
                or policy == "limited"
                and cap is None
            ):
                raise InvalidInput("explicit grid limit policy required")
            limits[direction + "_cap_kw"] = (
                0 if outage else None if policy == "unlimited" else cap
            )
        result.append(
            {
                **limits,
                "start_utc": period.get("start_utc"),
                "end_utc": period.get("end_utc"),
                "mode": period.get("mode"),
                "reserve_kwh": 0 if plant or no_storage else period.get("reserve_kwh"),
                "pv_enabled": False if storage_only else period.get("pv_enabled"),
                "allow_grid_charge": False
                if outage or no_storage
                else period.get("allow_grid_charge"),
            }
        )
    return result


def inventory(settings: Object) -> Object:
    value = object_value(settings.get("initial_inventory"), "initial inventory")
    note = value.get("source_note")
    if not isinstance(note, str) or not note.strip():
        raise InvalidInput("initial inventory requires its declared source")
    return InitialInventory.read({**value, "basis": "user_declared"}).model_dump(
        mode="json"
    )


def terminal(settings: Object) -> Json:
    policy = settings.get("terminal_policy")
    if policy == "none":
        return None
    if policy != "minimum" or settings.get("terminal_min_kwh") is None:
        raise InvalidInput("explicit terminal inventory policy required")
    return settings["terminal_min_kwh"]


class EnergyDeclarations:
    """One command's staged source-derived assets; publication joins admission."""

    def __init__(
        self,
        workspace: Workspace,
        actor: Actor,
        project_id: str,
        inputs: Object,
        products: ProductSources | None,
    ) -> None:
        self.workspace, self.actor, self.project_id = workspace, actor, project_id
        self.inputs, self.products = inputs, products
        self.staged: dict[str, Asset] = {}
        self.assets = Assets(workspace, staged=self.staged)

    def equipment(self, inputs: Object) -> Object:
        from .equipment_declarations import compile_equipment_inputs

        return compile_equipment_inputs(inputs, self.products)

    def battery(
        self, settings: Object, inputs: Object, *, unit_id: str | None = None
    ) -> str:
        note: Json
        dc = settings.get("dc")
        derived = unit_id is not None or settings.get("coupling") == "shared_dc"
        if derived:
            declared = object_value(dc, "DC loss assumptions")
            losses = object_value(declared.get("losses"), "DC losses")
            raw: Object = {
                "schema_version": 1,
                "model": "constant_window_shared_dc_bus_v1",
                "parameter_basis": "explicit_loss_scenario_with_woo_equipment",
                **losses,
                "battery_port_id": declared.get("battery_port_id"),
                "source_note": declared.get("source_note"),
            }
            for field in ("battery_temperature_c", "capacity_window_basis"):
                if field in declared:
                    raw[field] = declared[field]
            parameters = DcLossScenario.read(raw)
            if self.products is None:
                raise InvalidInput(
                    "current Woo source required for DC parameter derivation"
                )
            basis = self.products.equipment_basis()
            prepared = prepare_dc_parameters(inputs, basis, parameters)
            self.products.confirm_basis(basis, require_reference=False)
            dependencies: Object = {
                "dc_prepared_parameters": self.workspace.blobs.put_object(
                    prepared.model_dump(mode="json")
                ),
                "dc_woo_inputs": self.workspace.blobs.put_object(basis),
            }
            note = parameters.source_note
            content = encode(parameters.model_dump(mode="json", exclude_unset=True))
        else:
            note = settings.get("source_note")
            parameters_ac = BatteryParameters.read(
                {
                    "schema_version": 1,
                    "model": "constant_window_single_ac_bus_v1",
                    "parameter_basis": "explicit_scenario",
                    **object_value(settings.get("battery"), "battery parameters"),
                }
            )
            content, dependencies = encode(parameters_ac.model_dump(mode="json")), {}
        if not isinstance(note, str) or not note.strip():
            raise InvalidInput("battery parameters require their declared source")
        metadata: Object = {
            "retention": "permanent",
            "provenance": {
                "label": note,
                "basis": "user_explicit_scenario_not_equipment_release",
                "rights_basis": "user-declared numeric scenario, no third-party provider asset",
            },
        }
        if derived:
            metadata["dependencies"] = dependencies
        if unit_id is not None:
            metadata["equipment_unit_id"] = unit_id
        validate_asset(content, "application/json", "battery_parameters_v1", metadata)
        asset_id = uuid4().hex
        asset = Asset(
            asset_id,
            self.project_id,
            self.workspace.blobs.put(content),
            "application/json",
            "battery_parameters_v1",
            self.workspace.blobs.put_object(metadata),
            metadata,
        )
        self.staged[asset_id] = asset
        return asset_id

    def compile(self) -> Object:
        inputs = self.equipment(self.inputs)
        check_profile_selections(self.assets, self.actor, self.project_id, inputs)
        profiles = ProfileSelections.read(inputs.get("profile_selections")).selected
        joint = bool({"equipment_plant", "equipment_plant_setup"}.intersection(inputs))
        settings = object_value(
            inputs.get("energy_plant_setup" if joint else "energy_scenario"),
            "energy declarations",
        )
        coupling = settings.get("coupling", "plant_ac" if joint else "independent_ac")
        if (
            type(settings.get("schema_version")) is not int
            or settings["schema_version"] != 1
            or coupling
            not in (
                ("plant_ac", "plant_shared_dc")
                if joint
                else ("independent_ac", "shared_dc")
            )
        ):
            raise InvalidInput("unsupported energy declaration version or coupling")
        storage_only = storage_only_project(inputs)
        brief = inputs.get("brief")
        no_storage = isinstance(brief, dict) and brief.get("system_scope") == "pv_only"
        periods = schedule(
            settings.get("schedule"),
            storage_only=storage_only,
            plant=joint,
            no_storage=no_storage,
        )
        dc = not no_storage and coupling == (
            "plant_shared_dc" if joint else "shared_dc"
        )
        if (
            dc
            and joint
            and settings.get("controller")
            not in (None, "proportional_available_power_self_consumption_v1")
        ):
            raise InvalidInput(
                "DC plant replay supports the existing local DC then proportional AC controller"
            )
        pv_disabled = all(
            isinstance(p, dict) and p.get("pv_enabled") is False for p in periods
        )
        scenario: Object = {
            "schema_version": 1,
            "gross_load_asset_id": profiles.get("gross_load"),
            "critical_load_asset_id": profiles.get("critical_load"),
            "pv_available_asset_id": None
            if storage_only or not dc and pv_disabled
            else profiles.get("pv_available_ac"),
            "aux_ac_asset_id": profiles.get("aux_ac")
            if settings.get("aux_ac_kw") is None
            else None,
            "schedule": periods,
        }
        if settings.get("aux_ac_kw") is not None:
            scenario["aux_ac_kw"] = settings["aux_ac_kw"]
        if not joint:
            storage_settings = settings
            if no_storage:
                selected = inputs.get("equipment_selection")
                if isinstance(selected, dict):
                    fields = tuple(
                        field
                        for field in (
                            "battery_product_id",
                            "modules_per_stack",
                            "parallel_stacks",
                        )
                        if selected.get(field) is not None
                    )
                    if fields:
                        path = (
                            "equipment_setup"
                            if "equipment_setup" in inputs
                            else "equipment_selection"
                        )
                        raise InvalidInput(
                            "PV-only calculation cannot contain a selected battery",
                            fields=tuple(path + "." + field for field in fields),
                        )
                # No storage is a topology declaration. Zero state, throughput,
                # auxiliary and loss make the unused unity coefficients neutral.
                storage_settings = {
                    "source_note": "Project explicitly declares no storage (pv_only)",
                    "battery": {
                        "usable_window_kwh": 0,
                        "charge_ac_kw": 0,
                        "discharge_ac_kw": 0,
                        "eta_charge": 1,
                        "eta_discharge": 1,
                        "internal_aux_kw": 0,
                        "standing_loss_rate_per_hour": 0,
                    },
                    "initial_inventory": {
                        "pv_kwh": 0,
                        "grid_kwh": 0,
                        "initial_unknown_kwh": 0,
                        "source_note": "No storage exists in the declared topology",
                    },
                    "terminal_policy": "none",
                }
            scenario.update(
                battery_parameters_asset_id=self.battery(storage_settings, inputs),
                initial_inventory=inventory(storage_settings),
                terminal_min_kwh=terminal(storage_settings),
                controller=settings.get(
                    "controller", "self_consumption_with_reserve_v1"
                ),
            )
            if dc:
                declared = object_value(settings.get("dc"), "DC declarations")
                scenario.update(
                    coupling="shared_dc",
                    pv_converter_id=declared.get("pv_converter_id"),
                    aux_dc_kw=declared.get("aux_dc_kw"),
                )
            inputs["energy_replay"] = scenario
        else:
            plant = EquipmentPlant.from_inputs(inputs)
            if no_storage:
                scenario.update(
                    coupling="plant_ac",
                    units=[],
                    controller=settings.get(
                        "controller", "proportional_available_power_self_consumption_v1"
                    ),
                )
                inputs["energy_plant"] = scenario
                return inputs
            raw_units = settings.get("units")
            if not isinstance(raw_units, list):
                raise InvalidInput("storage unit energy declarations required")
            units: list[Json] = []
            for raw in raw_units:
                unit = object_value(raw, "storage unit")
                uid = unit.get("unit_id")
                if not isinstance(uid, str):
                    raise InvalidInput("storage unit identity required")
                declared = object_value(
                    unit.get("settings"), "unit energy declarations"
                )
                chosen = PlantEnergyKernel.unit_inputs(inputs, plant, uid)
                state: Object = {
                    "unit_id": uid,
                    "battery_parameters_asset_id": self.battery(
                        declared, chosen, unit_id=uid
                    ),
                    "initial_inventory": inventory(declared),
                    "reserve_kwh": unit.get("reserve_kwh"),
                    "terminal_min_kwh": terminal(declared),
                }
                if dc:
                    dc_settings = object_value(
                        declared.get("dc"), "unit DC declarations"
                    )
                    if type(unit.get("pv_dc_input_unused")) is not bool:
                        raise InvalidInput("explicit DC PV assignment required")
                    state.update(
                        pv_converter_id=None
                        if unit["pv_dc_input_unused"]
                        else dc_settings.get("pv_converter_id"),
                        aux_dc_kw=dc_settings.get("aux_dc_kw"),
                        allow_ac_charge=unit.get("allow_ac_charge"),
                    )
                else:
                    state["pv_dc_input_unused"] = unit.get("pv_dc_input_unused")
                units.append(state)
            scenario.update(
                coupling="plant_shared_dc" if dc else "plant_ac",
                units=units,
                controller="local_dc_then_proportional_ac_self_consumption_v1"
                if dc
                else settings.get(
                    "controller", "proportional_available_power_self_consumption_v1"
                ),
            )
            if dc:
                scenario.update(
                    pv_reference_asset_id=profiles.get("pv_reference"),
                    ac_pv_converter_ids=settings.get("ac_pv_converter_ids", []),
                )
            inputs["energy_plant"] = scenario
        return inputs

    def publish(self, connection: sqlite3.Connection) -> None:
        for asset in self.staged.values():
            connection.execute(
                "INSERT INTO project_assets (id, project_id, content_sha256, media_type, purpose, metadata_sha256, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    asset.id,
                    self.project_id,
                    asset.content_sha256,
                    asset.media_type,
                    asset.purpose,
                    asset.metadata_sha256,
                    self.workspace.clock(),
                ),
            )
