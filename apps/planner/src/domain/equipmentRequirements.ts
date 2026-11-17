import Ajv2020 from "ajv/dist/2020.js";
import schema from "../contracts/equipment-requirements.schema.json" with { type: "json" };
import type { JsonObject } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";

const validate = new Ajv2020({
	strict: true,
	strictNumbers: true,
}).compile<JsonObject>(schema);
export function readEquipmentRequirements(value: unknown): JsonObject {
	if (!validate(value))
		throw new ApiError(422, "equipment_requirements_incomplete");
	return value;
}
export function compileEquipmentRequirements(
	setup: JsonObject,
	declared: JsonObject = {},
): JsonObject {
	// Application belongs to project demand, not the hardware selection. Keep it
	// when preparing edited hardware fields from a saved search.
	const requirements: JsonObject = {
		...setup,
		...(declared.application !== undefined
			? { application: declared.application }
			: {}),
	};
	return readEquipmentRequirements(
		Object.fromEntries(
			Object.keys(schema.properties)
				.map((key) => [key, requirements[key]])
				.filter(([, value]) => value !== undefined),
		),
	);
}
