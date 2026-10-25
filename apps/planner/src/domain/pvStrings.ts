import Ajv2020 from "ajv/dist/2020.js";
import schema from "../contracts/pv-string-plan.schema.json" with { type: "json" };
import type { JsonObject } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";

export interface PvString extends JsonObject {
	id: string;
	mppt: number;
	input: number;
	module_ids: string[];
}
export interface PvStringPlan extends JsonObject {
	schema_version: 1;
	inverter_product_id: number;
	minimum_ambient_c: number | null;
	temperature_source: string | null;
	strings: PvString[];
}
const validate = new Ajv2020({
	strict: true,
	strictNumbers: true,
}).compile<PvStringPlan>(schema);
export function readPvStringPlan(value: unknown): PvStringPlan {
	if (!validate(value)) throw new ApiError(422, "pv_string_plan_incomplete");
	const ids = value.strings.map((s) => s.id),
		ports = value.strings.map((s) => `${s.mppt}:${s.input}`),
		modules = value.strings.flatMap((s) => s.module_ids);
	if ([ids, ports, modules].some((v) => v.length !== new Set(v).size))
		throw new ApiError(422, "pv_string_plan_incomplete");
	return value;
}
