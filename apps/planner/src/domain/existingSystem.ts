import type { JsonObject } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import { validate2020 } from "../data/schemaValidator.ts";
import schema from "../contracts/existing-system.schema.json" with { type: "json" };
import { equipmentDraft, type EquipmentUse } from "./equipment.ts";
import { hasPlant, readPlantDraft } from "./equipmentPlant.ts";
export interface ExistingSystem extends JsonObject {
	schema_version: 1;
	name: string;
	inverter_power_kw: number | null;
	keep_inverter: boolean;
}

const checkExisting = validate2020<ExistingSystem>(schema);
export function existingSystem(inputs: JsonObject): ExistingSystem | undefined {
	const value = inputs.existing_system;
	if (value === undefined) return undefined;
	if (!checkExisting(value)) throw new ApiError(422, "invalid_input");
	return value;
}

export function changeExistingSystem(
	current: JsonObject,
	patch: Partial<ExistingSystem> | null,
): JsonObject {
	const {
		existing_system: _previous,
		equipment_candidate: _candidate,
		...rest
	} = current;
	return patch === null
		? rest
		: {
				...rest,
				existing_system: {
					schema_version: 1,
					name: "",
					inverter_power_kw: null,
					keep_inverter: false,
					...existingSystem(current),
					...patch,
				},
			};
}

export function retainsUnverifiedInverter(inputs: JsonObject): boolean {
	if (existingSystem(inputs)?.keep_inverter !== true) return false;
	const primary = equipmentDraft(
		hasPlant(inputs)
			? (readPlantDraft(inputs).units[0]?.inputs ?? inputs)
			: inputs,
	);
	const use = primary.equipment_use as EquipmentUse | null | undefined;
	return !(
		typeof primary.inverter_product_id === "number" &&
		primary.inverter_product_id > 0 &&
		use?.inverter === "retain"
	);
}
