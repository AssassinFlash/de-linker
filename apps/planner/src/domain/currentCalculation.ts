import type { Json, JsonObject, Project } from "../data/protocol.ts";
import type { Draft } from "./draft.ts";
import { sameJson } from "./draft.ts";
import { comparisonModels, equipmentDraft } from "./equipment.ts";
import { hasPlant, readPlantDraft } from "./equipmentPlant.ts";

const isObject = (value: unknown): value is JsonObject =>
	value !== null && typeof value === "object" && !Array.isArray(value);

/** Plant-level requirements supply the operating mode for all its inverters. */
export function projectEquipmentScope(
	inputs: JsonObject,
): "none" | "products" | "system" {
	if (inputs.equipment_candidate) return "system";
	const plant = hasPlant(inputs) ? readPlantDraft(inputs) : null;
	const systems = (plant?.units.map((unit) => unit.inputs) ?? [inputs]).map(
		equipmentDraft,
	);
	const selected =
		plant?.parallel_groups.some(
			(group) => group.controller_product_id != null,
		) ||
		systems.some(
			(setup) =>
				setup.inverter_product_id != null ||
				setup.battery_product_id != null ||
				(Array.isArray(setup.accessory_product_ids) &&
					setup.accessory_product_ids.length > 0),
		);
	if (!selected) return "none";
	return systems.every(
		(setup) =>
			setup.inverter_product_id != null &&
			(plant ? plant.requirements : setup).operating_mode != null,
	)
		? "system"
		: "products";
}

function withoutBatteryBinding(value: JsonObject): JsonObject {
	const { battery_binding: _derived, ...authored } = value;
	return authored;
}

/** Only the calculation module's execution projections are removed. Other
 * project declarations and owned source selections remain the customer's input. */
export function authoredCalculationInputs(inputs: JsonObject): JsonObject {
	const { energy_replay: _single, energy_plant: _plant, ...remaining } = inputs;
	const authored: Record<string, Json> = { ...remaining };
	if (isObject(authored.energy_scenario))
		authored.energy_scenario = withoutBatteryBinding(authored.energy_scenario);
	const plant = authored.energy_plant_setup;
	if (isObject(plant) && Array.isArray(plant.units)) {
		authored.energy_plant_setup = {
			...plant,
			units: plant.units.map((unit) =>
				isObject(unit) && isObject(unit.settings)
					? { ...unit, settings: withoutBatteryBinding(unit.settings) }
					: unit,
			),
		};
	}
	return authored;
}

/** Demand evidence stays attached only while the inputs of the comparison agree. */
export function sameEquipmentDemand(
	left: JsonObject,
	right: JsonObject,
	checkGeometry = true,
): boolean {
	const a = authoredCalculationInputs(left),
		b = authoredCalculationInputs(right);
	const briefA = isObject(a.brief) ? a.brief : {};
	const briefB = isObject(b.brief) ? b.brief : {};
	return (
		["system_scope", "project_use", "site"].every((field) =>
			sameJson(briefA[field] ?? null, briefB[field] ?? null),
		) &&
		[
			"grid_connection",
			"country_rule_inputs",
			"backup_demand",
			"existing_system",
			"energy_scenario",
			"energy_plant_setup",
			"profile_selections",
			"equipment_demand",
			"pvgis_reference_setup",
			"pvgis_reference",
			...(checkGeometry ? ["geometry"] : []),
			"pv_generation",
			"pv_preparation",
			"geometric_pv_preparation",
		].every((field) => sameJson(a[field] ?? null, b[field] ?? null)) &&
		sameEquipmentModels(a, b)
	);
}

/** Compare the choices that filter discovery, independently of adopted hardware. */
export function sameEquipmentModels(
	left: JsonObject,
	right: JsonObject,
): boolean {
	function models(inputs: JsonObject, noBattery: boolean) {
		const setup = equipmentDraft(inputs);
		const preferences = comparisonModels(setup);
		const use = isObject(setup.equipment_use) ? setup.equipment_use : {};
		return {
			inverter:
				(use.inverter === "retain" ? setup : preferences).inverter_product_id ??
				null,
			battery: noBattery
				? null
				: ((use.battery === "retain" ? setup : preferences)
						.battery_product_id ?? null),
		};
	}
	function active(inputs: JsonObject) {
		const noBattery =
			isObject(inputs.brief) && inputs.brief.system_scope === "pv_only";
		if (!hasPlant(inputs)) return models(inputs, noBattery);
		const plant = readPlantDraft(inputs);
		return {
			units: plant.units.map((unit) => [
				unit.id,
				models(unit.inputs, noBattery),
			]),
			groups: plant.parallel_groups.map((group) => [
				group.id,
				group.controller_use === "retain" ||
				group.comparison_controller_product_id === undefined
					? group.controller_product_id
					: group.comparison_controller_product_id,
			]),
		};
	}
	return sameJson(active(left), active(right));
}

/** Match the server's authored discovery snapshot, retaining demand separately
 * from a candidate's physical selection. Explicit null is an answered filter. */
export function authoredDiscoveryInputs(inputs: JsonObject): JsonObject {
	const result = authoredCalculationInputs(inputs);
	const normalize = (source: JsonObject): JsonObject => {
		const { equipment_requirements: legacy, ...remaining } = source;
		const next: Record<string, Json> = { ...remaining };
		let setup = next.equipment_setup;
		if (!Object.hasOwn(next, "equipment_setup")) {
			if (isObject(next.equipment_selection)) {
				const { product_revisions: _revisions, ...hardware } =
					next.equipment_selection;
				setup = hardware;
			} else if (isObject(legacy)) {
				setup = {
					schema_version: 1,
					inverter_product_id: null,
					battery_product_id: null,
					modules_per_stack: null,
					parallel_stacks: null,
					accessory_product_ids: [],
					...Object.fromEntries(
						[
							"schema_version",
							"grid_phase",
							"operating_mode",
							"pv_dc_kw",
							"required_usable_kwh",
							"required_discharge_ac_kw",
						]
							.filter((key) => Object.hasOwn(legacy, key))
							.map((key) => [key, legacy[key]!]),
					),
				};
			}
		}
		if (isObject(setup))
			next.equipment_setup = {
				...setup,
				...(!Object.hasOwn(setup, "application") &&
				isObject(legacy) &&
				Object.hasOwn(legacy, "application")
					? { application: legacy.application! }
					: {}),
			};
		return next;
	};
	const { equipment_plant_requirements: _prepared, ...remaining } = result;
	const next: Record<string, Json> = { ...remaining };
	const plant = next.equipment_plant_setup;
	if (!isObject(plant)) return normalize(next);
	delete next.equipment_requirements;
	if (Array.isArray(plant.units))
		next.equipment_plant_setup = {
			...plant,
			units: plant.units.map((unit) =>
				isObject(unit) && isObject(unit.inputs)
					? { ...unit, inputs: normalize(unit.inputs) }
					: unit,
			),
		};
	return next;
}

/** Old adoption saved the recommended IDs in the editable equipment fields. */
export function needsComparisonModels(inputs: JsonObject): boolean {
	if (!inputs.equipment_candidate) return false;
	if (!hasPlant(inputs))
		return equipmentDraft(inputs).comparison_models === undefined;
	const plant = readPlantDraft(inputs);
	return (
		plant.units.some(
			(unit) => equipmentDraft(unit.inputs).comparison_models === undefined,
		) ||
		plant.parallel_groups.some(
			(group) => group.comparison_controller_product_id === undefined,
		)
	);
}

export function restoreComparisonModels(
	inputs: JsonObject,
	searched: JsonObject,
): JsonObject {
	function restore(current: JsonObject, previous: JsonObject): JsonObject {
		const setup = equipmentDraft(current);
		return setup.comparison_models === undefined
			? {
					...current,
					equipment_setup: {
						...setup,
						comparison_models: comparisonModels(equipmentDraft(previous)),
					},
				}
			: current;
	}
	if (!hasPlant(inputs)) return restore(inputs, searched);
	const plant = readPlantDraft(inputs);
	const before = readPlantDraft(searched);
	return {
		...inputs,
		equipment_plant_setup: {
			...plant,
			units: plant.units.map((unit) => {
				const prior = before.units.find((row) => row.id === unit.id);
				return prior
					? { ...unit, inputs: restore(unit.inputs, prior.inputs) }
					: unit;
			}),
			parallel_groups: plant.parallel_groups.map((group) => {
				const prior = before.parallel_groups.find((row) => row.id === group.id);
				if (!prior || group.comparison_controller_product_id !== undefined)
					return group;
				return {
					...group,
					comparison_controller_product_id:
						prior.comparison_controller_product_id === undefined
							? prior.controller_product_id
							: prior.comparison_controller_product_id,
				};
			}),
		},
	};
}

/** Confirm the snapshot captured by Calculate, preserving edits made while
 * the request was in flight. Calculation progress is not an editing step. */
export function acknowledgeCalculation(
	draft: Draft,
	expectedRevision: number,
	submittedInputs: JsonObject,
	project: Project,
	normalize: (inputs: JsonObject) => JsonObject = authoredCalculationInputs,
): Draft {
	if (
		project.id !== draft.baseline.id ||
		(project.revision !== expectedRevision &&
			project.revision !== expectedRevision + 1) ||
		!sameJson(project.inputs, submittedInputs)
	)
		throw new Error("invalid_calculation_snapshot");
	if (draft.baseline.revision > project.revision) return draft;
	if (
		draft.baseline.revision === project.revision &&
		(draft.baseline.input_sha256 !== project.input_sha256 ||
			!sameJson(draft.baseline.inputs, project.inputs))
	)
		throw new Error("invalid_calculation_snapshot");
	return {
		...draft,
		baseline: project,
		history: {
			...draft.history,
			past: draft.history.past.map(normalize),
			current: normalize(draft.history.current),
			future: draft.history.future.map(normalize),
		},
	};
}
