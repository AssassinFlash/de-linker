import { validate2020 } from "../data/schemaValidator.ts";
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
		? { modules_per_stack: assembly.fixed_modules_per_stack }
		: {};
}

/** Procurement intent per primary device; absent or null means new. */
export const PART_USES = ["new", "retain", "replace"] as const;
export type PartUse = (typeof PART_USES)[number];
export interface EquipmentUse extends JsonObject {
	inverter: PartUse;
	battery: PartUse;
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
	equipment_use?: EquipmentUse | null;
}
const validate = validate2020<EquipmentSelection>(schema);
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
			!Number.isSafeInteger(value.modules_per_stack * value.parallel_stacks)) ||
		(value.equipment_use != null &&
			value.equipment_use.battery !== "new" &&
			value.battery_product_id === null)
	)
		throw new ApiError(422, "equipment_selection_incomplete");
	return value;
}

const EQUIPMENT_SETUP_FIELDS = [
	"inverter_product_id",
	"battery_product_id",
	"modules_per_stack",
	"parallel_stacks",
	"operating_mode",
	"grid_phase",
	"pv_dc_kw",
	"required_usable_kwh",
	"required_discharge_ac_kw",
	"equipment_use",
	"comparison_models",
] as const;

/** Customer demand travels with the authored setup, never the physical selection. */
const EQUIPMENT_ROW_FIELDS = [
	"schema_version",
	"application",
	"accessory_product_ids",
	...EQUIPMENT_SETUP_FIELDS,
] as const;

function equipmentRow(row: JsonObject): JsonObject {
	return Object.fromEntries(
		EQUIPMENT_ROW_FIELDS.filter((key) => row[key] !== undefined).map((key) => [
			key,
			row[key] as Json,
		]),
	);
}

export function equipmentDraft(inputs: JsonObject): JsonObject {
	const noPv =
		inputs.brief !== undefined &&
		readObject(inputs.brief).system_scope === "storage_only";
	const scopeFields = noPv ? { pv_dc_kw: 0 } : {};
	const legacy =
		inputs.equipment_requirements === undefined
			? null
			: readObject(inputs.equipment_requirements);
	const application =
		legacy &&
		typeof legacy === "object" &&
		!Array.isArray(legacy) &&
		Object.hasOwn(legacy, "application")
			? { application: legacy.application! }
			: {};
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
		const use = row.equipment_use;
		if (
			use !== undefined &&
			use !== null &&
			(typeof use !== "object" ||
				!PART_USES.includes((use as JsonObject).inverter as PartUse) ||
				!PART_USES.includes((use as JsonObject).battery as PartUse))
		)
			throw new ApiError(422, "equipment_selection_incomplete");
		return { ...application, ...equipmentRow(row), ...scopeFields };
	}
	if (inputs.equipment_selection !== undefined)
		return {
			...equipmentRow(readEquipmentSelection(inputs.equipment_selection)),
			...application,
			...scopeFields,
		};
	if (inputs.equipment_requirements !== undefined)
		return {
			...equipmentDraft({}),
			...equipmentRow(readEquipmentRequirements(inputs.equipment_requirements)),
			...scopeFields,
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
		pv_dc_kw: noPv ? 0 : null,
		required_usable_kwh: null,
		required_discharge_ac_kw: null,
		equipment_use: null,
	};
}
const modelFields = ["inverter_product_id", "battery_product_id"] as const;

export function comparisonModels(setup: JsonObject): JsonObject {
	return (
		(setup.comparison_models as JsonObject | undefined) ?? {
			inverter_product_id: setup.inverter_product_id ?? null,
			battery_product_id: setup.battery_product_id ?? null,
		}
	);
}

export function changeEquipment(
	inputs: JsonObject,
	patch: JsonObject,
): JsonObject {
	const setup = equipmentDraft(inputs);
	const models = comparisonModels(setup);
	const next: Record<string, Json> = {
		...inputs,
		equipment_setup: {
			...setup,
			...(setup.comparison_models === undefined
				? {}
				: {
						comparison_models: {
							...models,
							...Object.fromEntries(
								modelFields
									.filter((key) => Object.hasOwn(patch, key))
									.map((key) => [key, patch[key]!]),
							),
						},
					}),
			...patch,
		},
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
	const {
		application: _demand,
		comparison_models: _filters,
		equipment_use,
		...hardware
	} = setup;
	const value = {
		...hardware,
		...(equipment_use == null ? {} : { equipment_use }),
		product_revisions: revisions,
	};
	return readEquipmentSelection(value);
}

/** A search result may not turn retained hardware into a different purchase. */
export function checkRetainedEquipment(
	setup: JsonObject,
	candidate: EquipmentSelection,
): void {
	const use = setup.equipment_use as EquipmentUse | null | undefined;
	const keys = [
		...(use?.inverter === "retain" ? ["inverter_product_id"] : []),
		...(use?.battery === "retain"
			? ["battery_product_id", "modules_per_stack", "parallel_stacks"]
			: []),
	];
	if (keys.some((key) => setup[key] !== candidate[key]))
		throw new ApiError(409, "retained_equipment_changed");
}
