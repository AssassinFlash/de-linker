import Ajv2020 from "ajv/dist/2020.js";
import schema from "../contracts/pv-plant-string-plan.schema.json" with { type: "json" };
import { ApiError } from "../data/protocol.ts";
import type { JsonObject } from "../data/protocol.ts";
import { readPvStringPlan } from "./pvStrings.ts";
import type { PvStringPlan } from "./pvStrings.ts";

export interface PvPlantStringUnit extends JsonObject {
	unit_id: string;
	inverter_instance_id: string | null;
	plan: PvStringPlan;
}
export interface PvPlantStringPlan extends JsonObject {
	schema_version: 1;
	units: PvPlantStringUnit[];
}
const validate = new Ajv2020({
	strict: true,
	strictNumbers: true,
}).compile<PvPlantStringPlan>(schema);
export function readPvPlantStringPlan(value: unknown): PvPlantStringPlan {
	if (!validate(value))
		throw new ApiError(422, "pv_plant_string_plan_incomplete");
	for (const unit of value.units) readPvStringPlan(unit.plan);
	const identities = [
		value.units.map((u) => u.unit_id),
		value.units.flatMap((u) =>
			u.inverter_instance_id === null ? [] : [u.inverter_instance_id],
		),
		value.units.flatMap((u) => u.plan.strings.map((s) => s.id)),
		value.units.flatMap((u) => u.plan.strings.flatMap((s) => s.module_ids)),
	];
	if (identities.some((ids) => ids.length !== new Set(ids).size))
		throw new ApiError(422, "pv_plant_string_plan_incomplete");
	return value;
}
/** A unit edit replaces only its own plan and always invalidates search adoption. */
export function changePvPlantStringUnit(
	inputs: JsonObject,
	unitId: string,
	unit: PvPlantStringUnit | null,
): JsonObject {
	const current =
		inputs.pv_plant_string_plan === undefined
			? { schema_version: 1 as const, units: [] }
			: readPvPlantStringPlan(inputs.pv_plant_string_plan);
	const units = current.units.filter((u) => u.unit_id !== unitId);
	if (unit) units.push(unit);
	const next = { ...inputs };
	delete next.equipment_candidate;
	delete next.pv_string_plan;
	if (units.length)
		next.pv_plant_string_plan = readPvPlantStringPlan({
			schema_version: 1,
			units,
		});
	else delete next.pv_plant_string_plan;
	return next;
}
