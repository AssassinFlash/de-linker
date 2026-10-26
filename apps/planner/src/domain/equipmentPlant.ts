import Ajv2020 from "ajv/dist/2020.js";
import schema from "../contracts/equipment-plant.schema.json" with { type: "json" };
import { ApiError } from "../data/protocol.ts";
import type { Json, JsonObject } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";
import type { EquipmentProduct } from "../data/equipmentProducts.ts";
import {
	compileEquipment,
	equipmentDraft,
	readEquipmentSelection,
	changeEquipment,
	factoryEquipment,
} from "./equipment.ts";
import type { EquipmentSelection } from "./equipment.ts";
import { compileEquipmentRequirements } from "./equipmentRequirements.ts";
import type { BatteryAssemblies } from "../data/equipmentProducts.ts";

export function factoryPlant(
	draft: PlantDraft,
	assemblies: BatteryAssemblies,
): PlantDraft {
	return {
		...draft,
		units: draft.units.map((unit) => ({
			...unit,
			inputs: changeEquipment(
				unit.inputs,
				factoryEquipment(equipmentDraft(unit.inputs), assemblies),
			),
		})),
	};
}

export interface PlantUnitDraft extends JsonObject {
	id: string;
	name: string;
	inputs: JsonObject;
}
export interface PlantGroupDraft extends JsonObject {
	id: string;
	unit_ids: string[];
	controller_product_id: number | null;
}
export interface PlantDraft extends JsonObject {
	schema_version: 1;
	requirements: JsonObject;
	units: PlantUnitDraft[];
	parallel_groups: PlantGroupDraft[];
}
export interface EquipmentPlant extends JsonObject {
	schema_version: 1;
	requirements: JsonObject;
	units: (JsonObject & {
		id: string;
		name: string;
		selection: EquipmentSelection;
	})[];
	parallel_groups: (PlantGroupDraft & { controller_revision: string | null })[];
}
const validate = new Ajv2020({
	strict: true,
	strictNumbers: true,
}).compile<EquipmentPlant>(schema);
const identity = /^[A-Za-z][A-Za-z0-9_-]{0,63}$/;
const incomplete = () => new ApiError(422, "equipment_plant_incomplete");
/** Create once per editing intent, outside a React state updater. */
export const plantIdentity = (kind: "system" | "group") =>
	`${kind}_${crypto.randomUUID()}`;

export function hasPlant(inputs: JsonObject): boolean {
	return (
		inputs.equipment_plant !== undefined ||
		inputs.equipment_plant_setup !== undefined
	);
}
const equipmentFields = [
	"equipment_plant",
	"equipment_plant_setup",
	"equipment_selection",
	"equipment_candidate",
	"equipment_setup",
	"equipment_requirements",
	"pv_string_plan",
] as const;
export function equipmentContext(inputs: JsonObject): JsonObject {
	return Object.fromEntries(
		equipmentFields
			.filter((key) => inputs[key] !== undefined)
			.map((key) => [key, inputs[key]!]),
	);
}
export function applyEquipmentContext(
	inputs: JsonObject,
	context: JsonObject,
): JsonObject {
	const next: Record<string, Json> = { ...inputs };
	for (const key of equipmentFields) delete next[key];
	return { ...next, ...context };
}
export function readEquipmentPlant(value: unknown): EquipmentPlant {
	if (!validate(value)) throw incomplete();
	const ids = new Set(value.units.map((u) => u.id));
	if (
		ids.size !== value.units.length ||
		new Set(value.parallel_groups.map((g) => g.id)).size !==
			value.parallel_groups.length
	)
		throw incomplete();
	const used = new Set<string>(),
		revisions = new Map<string, string>();
	const controllers = new Set(
		value.parallel_groups
			.map((g) => g.controller_product_id)
			.filter((id) => id !== null),
	);
	for (const unit of value.units) {
		readEquipmentSelection(unit.selection);
		for (const [id, revision] of Object.entries(
			unit.selection.product_revisions,
		)) {
			if (
				controllers.has(Number(id)) ||
				(revisions.has(id) && revisions.get(id) !== revision)
			)
				throw incomplete();
			revisions.set(id, revision);
		}
	}
	for (const group of value.parallel_groups) {
		if (
			new Set(group.unit_ids).size !== group.unit_ids.length ||
			group.unit_ids.some((id) => !ids.has(id) || used.has(id)) ||
			(group.controller_product_id === null) !==
				(group.controller_revision === null)
		)
			throw incomplete();
		for (const id of group.unit_ids) used.add(id);
		if (group.controller_product_id !== null) {
			const id = String(group.controller_product_id);
			if (revisions.has(id) && revisions.get(id) !== group.controller_revision)
				throw incomplete();
			revisions.set(id, group.controller_revision!);
		}
	}
	return value;
}
export function readPlantDraft(inputs: JsonObject): PlantDraft {
	if (inputs.equipment_plant_setup === undefined) {
		const plant = readEquipmentPlant(inputs.equipment_plant);
		return {
			schema_version: 1,
			requirements: plant.requirements,
			units: plant.units.map((u) => ({
				id: u.id,
				name: u.name,
				inputs: { equipment_selection: u.selection },
			})),
			parallel_groups: plant.parallel_groups.map(
				({ id, unit_ids, controller_product_id }) => ({
					id,
					unit_ids,
					controller_product_id,
				}),
			),
		};
	}
	const raw = readObject(inputs.equipment_plant_setup);
	if (
		raw.schema_version !== 1 ||
		!Array.isArray(raw.units) ||
		!raw.units.length ||
		!Array.isArray(raw.parallel_groups)
	)
		throw incomplete();
	const requirements = readObject(raw.requirements);
	const units = raw.units.map((value) => {
		const u = readObject(value),
			source = readObject(u.inputs);
		if (
			typeof u.id !== "string" ||
			!identity.test(u.id) ||
			typeof u.name !== "string" ||
			u.name.length > 256
		)
			throw incomplete();
		equipmentDraft(source);
		return { id: u.id, name: u.name, inputs: source };
	});
	const groups = raw.parallel_groups.map((value) => {
		const g = readObject(value);
		if (
			typeof g.id !== "string" ||
			!identity.test(g.id) ||
			!Array.isArray(g.unit_ids) ||
			g.unit_ids.some((id) => typeof id !== "string") ||
			(g.controller_product_id !== null &&
				(typeof g.controller_product_id !== "number" ||
					!Number.isSafeInteger(g.controller_product_id) ||
					g.controller_product_id <= 0))
		)
			throw incomplete();
		return {
			id: g.id,
			unit_ids: g.unit_ids as string[],
			controller_product_id: g.controller_product_id as number | null,
		};
	});
	if (
		new Set(units.map((u) => u.id)).size !== units.length ||
		new Set(groups.map((g) => g.id)).size !== groups.length
	)
		throw incomplete();
	return { schema_version: 1, requirements, units, parallel_groups: groups };
}
export function beginPlant(
	inputs: JsonObject,
	first: { id: string; name: string },
	second: { id: string; name: string },
): JsonObject {
	if (hasPlant(inputs)) return inputs;
	const setup = equipmentDraft(inputs),
		requirements: Record<string, Json> = {};
	for (const key of [
		"schema_version",
		"grid_phase",
		"operating_mode",
		"pv_dc_kw",
		"required_usable_kwh",
		"required_discharge_ac_kw",
	])
		requirements[key] = setup[key] ?? null;
	const draft: PlantDraft = {
		schema_version: 1,
		requirements,
		units: [
			{ ...first, inputs: { equipment_setup: setup } },
			{ ...second, inputs: { equipment_setup: equipmentDraft({}) } },
		],
		parallel_groups: [],
	};
	return plantInputs(inputs, draft);
}
export function plantInputs(inputs: JsonObject, draft: PlantDraft): JsonObject {
	const next: Record<string, Json> = {
		...inputs,
		equipment_plant_setup: draft,
	};
	for (const key of [
		"equipment_plant",
		"equipment_selection",
		"equipment_candidate",
		"equipment_setup",
		"equipment_requirements",
		"pv_string_plan",
	])
		delete next[key];
	return next;
}
export function singleSystem(inputs: JsonObject): JsonObject {
	const draft = readPlantDraft(inputs);
	if (draft.units.length !== 1 || draft.parallel_groups.length)
		throw incomplete();
	const next: Record<string, Json> = {
		...inputs,
		equipment_setup: {
			...equipmentDraft(draft.units[0]!.inputs),
			...draft.requirements,
		},
	};
	delete next.equipment_plant;
	delete next.equipment_plant_setup;
	return next;
}
export function compilePlant(
	draft: PlantDraft,
	products: readonly EquipmentProduct[],
): EquipmentPlant {
	try {
		const requirements = compileEquipmentRequirements(draft.requirements);
		return readEquipmentPlant({
			schema_version: 1,
			requirements,
			units: draft.units.map((u) => ({
				id: u.id,
				name: u.name,
				selection: compileEquipment(
					{
						...equipmentDraft(u.inputs),
						grid_phase: requirements.grid_phase ?? null,
						operating_mode: requirements.operating_mode ?? null,
					},
					products,
				),
			})),
			parallel_groups: draft.parallel_groups.map((g) => {
				const controller = products.find(
					(p) => p.id === g.controller_product_id,
				);
				if (g.controller_product_id !== null && !controller)
					throw new ApiError(409, "product_evidence_changed");
				return {
					...g,
					controller_revision: controller?.product_revision ?? null,
				};
			}),
		});
	} catch (error) {
		if (error instanceof ApiError && error.code === "product_evidence_changed")
			throw error;
		throw incomplete();
	}
}
