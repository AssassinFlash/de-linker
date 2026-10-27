import Ajv2020 from "ajv/dist/2020.js";
import schema from "../contracts/equipment-condition-inputs.schema.json" with { type: "json" };
import { ApiError } from "../data/protocol.ts";
import type { JsonObject } from "../data/protocol.ts";
import type { EquipmentProduct } from "../data/equipmentProducts.ts";
import { equipmentDraft, readEquipmentSelection } from "./equipment.ts";
import {
	hasPlant,
	readEquipmentPlant,
	readPlantDraft,
} from "./equipmentPlant.ts";
import { sameJson } from "./draft.ts";

export type DeviceRole = "inverter" | "battery" | "accessory";
export type EquipmentSelectionRef =
	| { kind: "single"; role: DeviceRole }
	| { kind: "plant_unit"; unit_id: string; role: DeviceRole }
	| { kind: "plant_controller"; group_id: string };
export interface DeviceConditionInput extends JsonObject {
	selection_ref: EquipmentSelectionRef;
	product_id: number;
	product_revision: string;
	declared_model: string | null;
	declared_firmware: string | null;
	source_note: string | null;
}
export interface EquipmentConditionInputs extends JsonObject {
	schema_version: 1;
	devices: DeviceConditionInput[];
}
export interface ConditionTarget {
	selection_ref: EquipmentSelectionRef;
	product_id: number;
	product_revision: string | null;
	unit_name: string | null;
	group_index: number | null;
	model: string | null;
}
const validate = new Ajv2020({
	strict: true,
	strictNumbers: true,
}).compile<EquipmentConditionInputs>(schema);
export function conditionDeviceKey(device: {
	selection_ref: EquipmentSelectionRef;
	product_id: number;
}): string {
	const ref = device.selection_ref;
	return JSON.stringify([
		ref.kind,
		ref.kind === "plant_unit"
			? ref.unit_id
			: ref.kind === "plant_controller"
				? ref.group_id
				: null,
		ref.kind === "plant_controller" ? null : ref.role,
		device.product_id,
	]);
}
export function readEquipmentConditionInputs(
	value: unknown,
): EquipmentConditionInputs {
	if (
		!validate(value) ||
		new Set(value.devices.map(conditionDeviceKey)).size !== value.devices.length
	)
		throw new ApiError(422, "invalid_input");
	return value;
}

/** Read selected identities; current Woo data supplies reference labels only. */
export function equipmentConditionTargets(
	inputs: JsonObject,
	products: readonly EquipmentProduct[],
): ConditionTarget[] {
	const targets: ConditionTarget[] = [];
	const add = (
		ref: EquipmentSelectionRef,
		id: number,
		revision: string | null,
		unit_name: string | null,
		group_index: number | null = null,
	) => {
		const product = products.find((p) => p.id === id);
		targets.push({
			selection_ref: ref,
			product_id: id,
			product_revision: revision ?? product?.product_revision ?? null,
			unit_name,
			group_index,
			model: product?.model ?? null,
		});
	};
	const selection = (
		source: JsonObject,
		unit_id: string | null,
		name: string | null,
	) => {
		const prepared =
			source.equipment_selection === undefined
				? null
				: readEquipmentSelection(source.equipment_selection);
		const draft = prepared ?? equipmentDraft(source);
		for (const [role, ids] of [
			["inverter", [draft.inverter_product_id]],
			["battery", [draft.battery_product_id]],
			["accessory", draft.accessory_product_ids],
		] as const) {
			for (const id of Array.isArray(ids) ? ids : []) {
				if (typeof id !== "number") continue;
				add(
					unit_id === null
						? { kind: "single", role }
						: { kind: "plant_unit", unit_id, role },
					id,
					prepared?.product_revisions[String(id)] ?? null,
					name,
				);
			}
		}
	};
	if (hasPlant(inputs)) {
		const prepared =
			inputs.equipment_plant === undefined
				? null
				: readEquipmentPlant(inputs.equipment_plant);
		const draft = readPlantDraft(
			prepared ? { equipment_plant: prepared } : inputs,
		);
		for (const unit of draft.units) {
			const pinned = prepared?.units.find((u) => u.id === unit.id);
			selection(
				pinned ? { equipment_selection: pinned.selection } : unit.inputs,
				unit.id,
				unit.name,
			);
		}
		for (const [index, group] of draft.parallel_groups.entries()) {
			if (group.controller_product_id === null) continue;
			const pinned = prepared?.parallel_groups.find((g) => g.id === group.id);
			add(
				{ kind: "plant_controller", group_id: group.id },
				group.controller_product_id,
				pinned?.controller_revision ?? null,
				null,
				index + 1,
			);
		}
	} else selection(inputs, null, null);
	return targets;
}

export function conditionBindingMatches(
	device: DeviceConditionInput,
	target: ConditionTarget,
): boolean {
	return (
		conditionDeviceKey(device) === conditionDeviceKey(target) &&
		(target.product_revision === null ||
			device.product_revision === target.product_revision)
	);
}

/** No implicit object/default on old projects; values never undergo numeric/version coercion. */
export function changeDeviceCondition(
	inputs: JsonObject,
	target: ConditionTarget,
	patch: Partial<
		Pick<
			DeviceConditionInput,
			"declared_model" | "declared_firmware" | "source_note"
		>
	>,
	products: readonly EquipmentProduct[],
): JsonObject {
	const current =
		inputs.equipment_condition_inputs === undefined
			? { schema_version: 1 as const, devices: [] }
			: readEquipmentConditionInputs(inputs.equipment_condition_inputs);
	const live = equipmentConditionTargets(inputs, products).find(
		(candidate) => conditionDeviceKey(candidate) === conditionDeviceKey(target),
	);
	if (!live || !target.product_revision || !sameJson(live, target))
		throw new ApiError(409, "conflict");
	const key = conditionDeviceKey(target),
		previous = current.devices.find((d) => conditionDeviceKey(d) === key);
	if (previous && !conditionBindingMatches(previous, target))
		throw new ApiError(409, "product_evidence_changed");
	const value: DeviceConditionInput = {
		selection_ref: target.selection_ref,
		product_id: target.product_id,
		product_revision: target.product_revision,
		declared_model: null,
		declared_firmware: null,
		source_note: null,
		...previous,
		...Object.fromEntries(
			Object.entries(patch).map(([field, value]) => [
				field,
				typeof value === "string" && !value.trim() ? null : value,
			]),
		),
	};
	return {
		...inputs,
		equipment_condition_inputs: readEquipmentConditionInputs({
			schema_version: 1,
			devices: previous
				? current.devices.map((device) =>
						conditionDeviceKey(device) === key ? value : device,
					)
				: [...current.devices, value],
		}),
	};
}

export function removeDeviceCondition(
	inputs: JsonObject,
	device: DeviceConditionInput,
): JsonObject {
	const current = readEquipmentConditionInputs(
		inputs.equipment_condition_inputs,
	);
	return {
		...inputs,
		equipment_condition_inputs: {
			...current,
			devices: current.devices.filter((d) => !sameJson(d, device)),
		},
	};
}
