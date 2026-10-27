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
export function compileEquipmentRequirements(setup: JsonObject): JsonObject {
	return readEquipmentRequirements(
		Object.fromEntries(
			Object.keys(schema.properties).map((key) => [key, setup[key]]),
		),
	);
}
