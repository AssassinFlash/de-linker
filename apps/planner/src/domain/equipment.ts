import Ajv2020 from "ajv/dist/2020.js";
import schema from "../contracts/equipment-selection.schema.json" with { type: "json" };
import type { Json, JsonObject } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";
import { readEquipmentRequirements } from "./equipmentRequirements.ts";
import type {
	EquipmentProduct,
	BatteryAssemblies,
} from "../data/equipmentProducts.ts";

/** Applied by explicit preparation; never mutates an older saved selection. */
export function factoryEquipment(
	setup: JsonObject,
	assemblies: BatteryAssemblies,
): JsonObject {
	const assembly = assemblies[String(setup.battery_product_id)];
	return assembly?.sales_unit_kind === "battery_system" &&
		assembly.fixed_modules_per_stack !== null
		? { ...setup, modules_per_stack: assembly.fixed_modules_per_stack }
		: setup;
}

export interface EquipmentSelection extends JsonObject {
	schema_version: 1;
	inverter_product_id: number;
	battery_product_id: number | null;
	modules_per_stack: number | null;
	parallel_stacks: number | null;
	accessory_product_ids: number[];
	grid_phase: 1 | 3 | null;
	operating_mode: "grid_connected" | "backup";
	pv_dc_kw: number | null;
	required_usable_kwh: number | null;
	required_discharge_ac_kw: number | null;
	product_revisions: Record<string, string>;
}
const validate = new Ajv2020({
	strict: true,
	strictNumbers: true,
}).compile<EquipmentSelection>(schema);
export function readEquipmentSelection(value: unknown): EquipmentSelection {
	if (!validate(value))
		throw new ApiError(422, "equipment_selection_incomplete");
	const selected = [
		value.inverter_product_id,
		...(value.battery_product_id === null ? [] : [value.battery_product_id]),
		...value.accessory_product_ids,
	];
	if (
		new Set(value.accessory_product_ids).size !==
			value.accessory_product_ids.length ||
		value.accessory_product_ids.includes(value.inverter_product_id) ||
		(value.battery_product_id !== null &&
			value.accessory_product_ids.includes(value.battery_product_id)) ||
		Object.keys(value.product_revisions).sort().join() !==
			[...new Set(selected)].map(String).sort().join() ||
		(value.modules_per_stack !== null &&
			value.parallel_stacks !== null &&
			!Number.isSafeInteger(value.modules_per_stack * value.parallel_stacks))
	)
		throw new ApiError(422, "equipment_selection_incomplete");
	return value;
}
export function equipmentDraft(inputs: JsonObject): JsonObject {
	if (inputs.equipment_setup !== undefined) {
		const row = readObject(inputs.equipment_setup);
		if (
			row.schema_version !== 1 ||
			!Array.isArray(row.accessory_product_ids) ||
			!row.accessory_product_ids.every(
				(id) => typeof id === "number" && Number.isSafeInteger(id) && id > 0,
			) ||
			!([null, "grid_connected", "backup"] as unknown[]).includes(
				row.operating_mode,
			) ||
			!([null, 1, 3] as unknown[]).includes(row.grid_phase)
		)
			throw new ApiError(422, "equipment_selection_incomplete");
		for (const key of [
			"inverter_product_id",
			"battery_product_id",
			"modules_per_stack",
			"parallel_stacks",
			"pv_dc_kw",
			"required_usable_kwh",
			"required_discharge_ac_kw",
		]) {
			const n = row[key];
			if (
				n !== null &&
				(typeof n !== "number" ||
					!Number.isFinite(n) ||
					n < 0 ||
					Math.abs(n) > Number.MAX_SAFE_INTEGER)
			)
				throw new ApiError(422, "equipment_selection_incomplete");
		}
		return row;
	}
	if (inputs.equipment_selection !== undefined)
		return readEquipmentSelection(inputs.equipment_selection);
	if (inputs.equipment_requirements !== undefined)
		return {
			...equipmentDraft({}),
			...readEquipmentRequirements(inputs.equipment_requirements),
		};
	return {
		schema_version: 1,
		inverter_product_id: null,
		battery_product_id: null,
		modules_per_stack: null,
		parallel_stacks: null,
		accessory_product_ids: [],
		grid_phase: null,
		operating_mode: null,
		pv_dc_kw: null,
		required_usable_kwh: null,
		required_discharge_ac_kw: null,
	};
}
export function changeEquipment(
	inputs: JsonObject,
	patch: JsonObject,
): JsonObject {
	const next: Record<string, Json> = {
		...inputs,
		equipment_setup: { ...equipmentDraft(inputs), ...patch },
	};
	delete next.equipment_selection;
	delete next.equipment_candidate;
	return next;
}
export function compileEquipment(
	setup: JsonObject,
	products: readonly EquipmentProduct[],
): EquipmentSelection {
	const selected = [
		setup.inverter_product_id,
		setup.battery_product_id,
		...(Array.isArray(setup.accessory_product_ids)
			? setup.accessory_product_ids
			: []),
	].filter((id) => id !== null);
	const revisions: Record<string, string> = {};
	for (const id of selected) {
		const product = products.find((p) => p.id === id);
		if (!product) throw new ApiError(409, "product_evidence_changed");
		revisions[String(product.id)] = product.product_revision;
	}
	const value = { ...setup, product_revisions: revisions };
	return readEquipmentSelection(value);
}
