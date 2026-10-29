import Ajv2020 from "ajv/dist/2020.js";
import schema from "../contracts/plant-energy-inputs.schema.json" with { type: "json" };
import dcSchema from "../contracts/dc-plant-energy-inputs.schema.json" with { type: "json" };
import { ApiError, type JsonObject } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";
import { sameJson } from "./draft.ts";
import { DC_MODEL, emptyDcScenario, readDcLossScenario } from "./dcEnergy.ts";
import type { DcLossScenario } from "./dcEnergy.ts";
import {
	compileInitialInventory,
	compileOperatingPeriods,
	compileTerminalMinimum,
	emptyScenario,
	readScenarioDraft,
} from "./energyScenario.ts";
import type { PeriodDraft, ScenarioDraft } from "./energyScenario.ts";
import type { EquipmentPlant } from "./equipmentPlant.ts";
import type { ProfileSelections } from "./profiles.ts";
import { dropGeometricRoofAc, geometricRoofAssetId } from "./profiles.ts";

export const PLANT_ENERGY_TASK = "plant_ac_energy_replay_v1";
export const PLANT_ENERGY_MODEL = "distinct_woo_battery_only_ac_equivalents_v1";
export const DC_PLANT_ENERGY_TASK = "plant_shared_dc_energy_replay_v1";
export const DC_PLANT_ENERGY_MODEL = "distinct_woo_shared_dc_ports_v1";
export const isPlantEnergyTask = (kind: unknown): boolean =>
	kind === PLANT_ENERGY_TASK || kind === DC_PLANT_ENERGY_TASK;
export const plantEnergyTask = (setup: PlantEnergyDraft): string =>
	setup.coupling === "plant_shared_dc"
		? DC_PLANT_ENERGY_TASK
		: PLANT_ENERGY_TASK;

export interface PlantEnergyUnitDraft extends JsonObject {
	readonly unit_id: string;
	readonly settings: ScenarioDraft;
	readonly reserve_kwh: number | null;
	readonly pv_dc_input_unused: boolean | null;
	readonly allow_ac_charge?: boolean | null;
}
export interface PlantEnergyDraft extends JsonObject {
	readonly schema_version: 1;
	readonly coupling?: "plant_ac" | "plant_shared_dc";
	readonly ac_pv_converter_ids?: readonly string[];
	readonly schedule: readonly PeriodDraft[];
	readonly units: readonly PlantEnergyUnitDraft[];
}
export interface PlantEnergyInputs extends JsonObject {
	readonly schema_version: 1;
	readonly coupling: "plant_ac" | "plant_shared_dc";
	readonly gross_load_asset_id: string;
	readonly critical_load_asset_id: string | null;
	readonly pv_available_asset_id: string | null;
	readonly aux_ac_asset_id: string;
	readonly units: readonly (JsonObject & {
		unit_id: string;
		battery_parameters_asset_id: string;
	})[];
}
const check = new Ajv2020({
	strict: true,
	strictNumbers: true,
}).compile<PlantEnergyInputs>(schema);
const checkDC = new Ajv2020({
	strict: true,
	strictNumbers: true,
}).compile<PlantEnergyInputs>(dcSchema);
export function readPlantEnergyInputs(value: unknown): PlantEnergyInputs {
	const candidate = readObject(value);
	if (
		!(candidate.coupling === "plant_shared_dc" ? checkDC(value) : check(value))
	)
		throw new ApiError(422, "invalid_plant_energy_inputs");
	return value as PlantEnergyInputs;
}

export function emptyPlantUnit(unit_id: string): PlantEnergyUnitDraft {
	return {
		unit_id,
		settings: {
			...emptyScenario(),
			coupling: "shared_dc",
			dc: { ...emptyDcScenario(), aux_dc_kw: 0 },
		},
		reserve_kwh: null,
		pv_dc_input_unused: null,
		allow_ac_charge: null,
	};
}

/** Keep physical identities across edits; new devices start without guessed states. */
export function plantEnergyDraft(
	inputs: JsonObject,
	plant: EquipmentPlant,
): PlantEnergyDraft {
	if (inputs.energy_plant_setup === undefined) {
		return {
			schema_version: 1,
			coupling: plant.units.some((u) => (u.selection.pv_dc_kw ?? 0) > 0)
				? "plant_shared_dc"
				: "plant_ac",
			ac_pv_converter_ids: [],
			schedule: emptyScenario().schedule.map((p) => ({ ...p, reserve_kwh: 0 })),
			units: plant.units.map((u) => emptyPlantUnit(u.id)),
		};
	}
	const raw = readObject(inputs.energy_plant_setup);
	if (raw.schema_version !== 1 || !Array.isArray(raw.units))
		throw new ApiError(422, "invalid_plant_energy_inputs");
	if (
		raw.coupling !== undefined &&
		raw.coupling !== "plant_ac" &&
		raw.coupling !== "plant_shared_dc"
	)
		throw new ApiError(422, "invalid_plant_energy_inputs");
	const acGroups = raw.ac_pv_converter_ids ?? [];
	if (
		!Array.isArray(acGroups) ||
		acGroups.some((id) => typeof id !== "string" || !id.trim()) ||
		new Set(acGroups).size !== acGroups.length
	)
		throw new ApiError(422, "invalid_plant_energy_inputs");
	const schedule = readScenarioDraft({
		...emptyScenario(),
		schedule: raw.schedule,
	}).schedule;
	const saved = raw.units.map((value) => {
		const u = readObject(value);
		if (
			typeof u.unit_id !== "string" ||
			!(
				u.reserve_kwh === null ||
				(typeof u.reserve_kwh === "number" &&
					Number.isFinite(u.reserve_kwh) &&
					u.reserve_kwh >= 0)
			) ||
			!(
				u.pv_dc_input_unused === null ||
				typeof u.pv_dc_input_unused === "boolean"
			)
		)
			throw new ApiError(422, "invalid_plant_energy_inputs");
		return {
			unit_id: u.unit_id,
			settings: readScenarioDraft(u.settings),
			reserve_kwh: u.reserve_kwh,
			pv_dc_input_unused: u.pv_dc_input_unused,
			allow_ac_charge:
				u.allow_ac_charge === undefined || u.allow_ac_charge === null
					? null
					: typeof u.allow_ac_charge === "boolean"
						? u.allow_ac_charge
						: (() => {
								throw new ApiError(422, "invalid_plant_energy_inputs");
							})(),
		};
	});
	if (new Set(saved.map((u) => u.unit_id)).size !== saved.length)
		throw new ApiError(422, "invalid_plant_energy_inputs");
	return {
		schema_version: 1,
		coupling:
			raw.coupling === "plant_shared_dc" ? "plant_shared_dc" : "plant_ac",
		ac_pv_converter_ids: acGroups as readonly string[],
		schedule,
		units: plant.units.map(
			(u) => saved.find((s) => s.unit_id === u.id) ?? emptyPlantUnit(u.id),
		),
	};
}

export function plantEnergyParameters(
	unit: PlantEnergyUnitDraft,
): DcLossScenario {
	const dc = unit.settings.dc;
	if (!dc?.source_note.trim())
		throw new ApiError(422, "battery_source_required");
	return readDcLossScenario({
		schema_version: 1,
		model: DC_MODEL,
		parameter_basis: "explicit_loss_scenario_with_woo_equipment",
		...dc.losses,
		battery_port_id: dc.battery_port_id,
		...(dc.battery_temperature_c === undefined
			? {}
			: { battery_temperature_c: dc.battery_temperature_c }),
		...(dc.capacity_window_basis === undefined
			? {}
			: { capacity_window_basis: dc.capacity_window_basis }),
		source_note: dc.source_note,
	});
}

export function plantEnergyParts(
	draft: PlantEnergyDraft,
	profiles: ProfileSelections,
	plant: EquipmentPlant,
	inputs: JsonObject = {},
): { parameters: ReadonlyMap<string, DcLossScenario>; inputs: JsonObject } {
	const { gross_load, critical_load, pv_available_ac, pv_reference, aux_ac } =
		profiles.selected;
	const dcPlant = draft.coupling === "plant_shared_dc";
	if (
		dcPlant &&
		pv_reference &&
		pv_available_ac &&
		(pv_reference === pv_available_ac ||
			pv_available_ac === geometricRoofAssetId(inputs))
	)
		throw new ApiError(422, "plant_dc_duplicate_pv_source");
	if (!gross_load || (!dcPlant && !pv_available_ac) || !aux_ac)
		throw new ApiError(422, "scenario_profiles_required");
	if (
		!dcPlant &&
		(plant.requirements.pv_dc_kw !== 0 ||
			plant.units.some((u) => u.selection.pv_dc_kw !== 0))
	)
		throw new ApiError(422, "plant_energy_dc_pv_used");
	if (
		plant.units.length !== draft.units.length ||
		plant.units.some((u) => !draft.units.some((s) => s.unit_id === u.id))
	)
		throw new ApiError(422, "invalid_plant_energy_inputs");
	const parameters = new Map<string, DcLossScenario>();
	const units: JsonObject[] = draft.units.map((unit) => {
		if (!dcPlant && unit.pv_dc_input_unused !== true)
			throw new ApiError(422, "plant_energy_dc_pv_used");
		if (unit.reserve_kwh === null)
			throw new ApiError(422, "operating_period_incomplete");
		parameters.set(unit.unit_id, plantEnergyParameters(unit));
		const state = {
			unit_id: unit.unit_id,
			initial_inventory: compileInitialInventory(
				unit.settings.initial_inventory,
			),
			reserve_kwh: unit.reserve_kwh,
			terminal_min_kwh: compileTerminalMinimum(unit.settings),
		};
		if (!dcPlant) return { ...state, pv_dc_input_unused: true };
		const pvGroup = unit.settings.dc?.pv_converter_id.trim() ?? "";
		if (
			unit.pv_dc_input_unused === null ||
			(unit.pv_dc_input_unused !== true && !pvGroup) ||
			unit.settings.dc?.aux_dc_kw == null ||
			typeof unit.allow_ac_charge !== "boolean"
		)
			throw new ApiError(422, "plant_dc_assignment_required");
		if (
			unit.pv_dc_input_unused === true &&
			plant.units.find((u) => u.id === unit.unit_id)!.selection.pv_dc_kw !== 0
		)
			throw new ApiError(422, "plant_dc_assignment_required");
		return {
			...state,
			pv_converter_id: unit.pv_dc_input_unused === true ? null : pvGroup,
			aux_dc_kw: unit.settings.dc!.aux_dc_kw,
			allow_ac_charge: unit.allow_ac_charge,
		};
	});
	return {
		parameters,
		inputs: {
			schema_version: 1,
			coupling: dcPlant ? "plant_shared_dc" : "plant_ac",
			gross_load_asset_id: gross_load,
			critical_load_asset_id: critical_load ?? null,
			pv_available_asset_id: pv_available_ac ?? null,
			...(dcPlant
				? {
						pv_reference_asset_id: pv_reference ?? null,
						ac_pv_converter_ids: draft.ac_pv_converter_ids ?? [],
					}
				: {}),
			aux_ac_asset_id: aux_ac,
			schedule: compileOperatingPeriods(
				draft.schedule.map((p) => ({ ...p, reserve_kwh: 0 })),
				critical_load,
			),
			units,
			controller: dcPlant
				? "local_dc_then_proportional_ac_self_consumption_v1"
				: "proportional_available_power_self_consumption_v1",
		},
	};
}

export function compilePlantEnergy(
	draft: PlantEnergyDraft,
	profiles: ProfileSelections,
	plant: EquipmentPlant,
	inputs: JsonObject = {},
): PlantEnergyInputs {
	const parts = plantEnergyParts(draft, profiles, plant, inputs);
	const units = (parts.inputs.units as readonly JsonObject[]).map((unit) => {
		const settings = draft.units.find(
			(u) => u.unit_id === unit.unit_id,
		)!.settings;
		const binding = settings.battery_binding,
			parameters = parts.parameters.get(String(unit.unit_id))!;
		const selection = plant.units.find((u) => u.id === unit.unit_id)!.selection;
		if (
			!binding ||
			!sameJson(binding.parameters, parameters) ||
			binding.source_note !== parameters.source_note ||
			!sameJson(binding.equipment_selection, selection)
		)
			throw new ApiError(422, "battery_not_prepared");
		return { ...unit, battery_parameters_asset_id: binding.asset_id };
	});
	return readPlantEnergyInputs({ ...parts.inputs, units });
}

export function plantEnergyInputs(
	inputs: JsonObject,
	setup: PlantEnergyDraft,
): JsonObject {
	const { energy_plant: _old, energy_replay: _single, ...rest } = inputs;
	const base =
		setup.coupling === "plant_shared_dc" ? dropGeometricRoofAc(rest) : rest;
	return { ...base, energy_plant_setup: setup };
}
