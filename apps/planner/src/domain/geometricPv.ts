/** A separately named AC scenario; existing unshaded profiles keep their identity. */
import Ajv2020 from "ajv/dist/2020.js";
import schema from "../contracts/geometric-pv.schema.json" with { type: "json" };
import type { JsonObject } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";
import type { PvDraft } from "./solarSetup.ts";
import { compilePv, emptyPv, readSolarSetup } from "./solarSetup.ts";
import { sameJson } from "./draft.ts";
import { invalidateEnergyReplay } from "./energyScenario.ts";

export const GEOMETRIC_PV_TASK = "prepare_geometric_pv_reference_v1";
export const GEOMETRIC_PV_PURPOSE = "geometric_pv_reference_profile_v1";
export const GEOMETRIC_PV_MODEL = "opaque_direct_uniform_pvlib_reference_v1";
export interface GeometricPvDraft extends JsonObject {
	readonly schema_version: 1;
	readonly model: typeof GEOMETRIC_PV_MODEL;
	readonly weather_asset_id: string | null;
	readonly sampling: {
		readonly coarse_cells_per_edge: number | null;
		readonly fine_cells_per_edge: number | null;
	};
	readonly diffuse_policy: "retain_unobstructed_sky_and_ground_components_v1";
	readonly thermal_policy: "sapm_from_module_mean_poa_v1";
	readonly electrical_policy: "uniform_module_pvwatts_independent_mpp_sum_v1";
	readonly parameters: PvDraft;
}
export interface GeometricPvLimits {
	readonly max_module_steps: number;
	readonly max_samples: number;
	readonly max_ray_face_checks: number;
	readonly max_bounds_checks: number;
	readonly index_leaf_size: number;
}
const check = new Ajv2020({ strict: true, strictNumbers: true }).compile(
	schema,
);
export function emptyGeometricPv(
	parameters: PvDraft = emptyPv(),
): GeometricPvDraft {
	return {
		schema_version: 1,
		model: GEOMETRIC_PV_MODEL,
		weather_asset_id: null,
		sampling: { coarse_cells_per_edge: null, fine_cells_per_edge: null },
		diffuse_policy: "retain_unobstructed_sky_and_ground_components_v1",
		thermal_policy: "sapm_from_module_mean_poa_v1",
		electrical_policy: "uniform_module_pvwatts_independent_mpp_sum_v1",
		parameters,
	};
}
export function geometricPvDraft(inputs: JsonObject): GeometricPvDraft {
	if (inputs.geometric_pv_preparation === undefined)
		return emptyGeometricPv(readSolarSetup(inputs).pv);
	const row = readObject(inputs.geometric_pv_preparation),
		sampling = readObject(row.sampling),
		constants = emptyGeometricPv();
	if (
		Object.keys(row).sort().join() !== Object.keys(constants).sort().join() ||
		(
			[
				"schema_version",
				"model",
				"diffuse_policy",
				"thermal_policy",
				"electrical_policy",
			] as const
		).some((key) => row[key] !== constants[key]) ||
		(row.weather_asset_id !== null &&
			(typeof row.weather_asset_id !== "string" ||
				!/^[a-f0-9]{32}$/.test(row.weather_asset_id))) ||
		Object.keys(sampling).sort().join() !==
			"coarse_cells_per_edge,fine_cells_per_edge" ||
		Object.values(sampling).some(
			(n) => n !== null && (typeof n !== "number" || !Number.isFinite(n)),
		)
	)
		throw new ApiError(422, "geometric_pv_inputs_invalid");
	readSolarSetup({ pv_generation: row.parameters! });
	return row as GeometricPvDraft;
}
export function compileGeometricPv(
	value: GeometricPvDraft,
	geometry: unknown,
): JsonObject {
	if (
		!check(value) ||
		!Number.isSafeInteger(value.sampling.coarse_cells_per_edge) ||
		!Number.isSafeInteger(value.sampling.fine_cells_per_edge) ||
		Number(value.sampling.fine_cells_per_edge) <=
			Number(value.sampling.coarse_cells_per_edge)
	)
		throw new ApiError(422, "geometric_pv_inputs_invalid");
	compilePv(value.parameters, geometry);
	return value;
}
export function geometricPvInputs(
	inputs: JsonObject,
	next: GeometricPvDraft,
): JsonObject {
	geometricPvDraft({ geometric_pv_preparation: next });
	return sameJson(inputs.geometric_pv_preparation, next)
		? inputs
		: { ...invalidateEnergyReplay(inputs), geometric_pv_preparation: next };
}
export function removeGeometricPv(inputs: JsonObject): JsonObject {
	const next = { ...invalidateEnergyReplay(inputs) };
	delete next.geometric_pv_preparation;
	return next;
}
export function readGeometricPvLimits(value: unknown): GeometricPvLimits {
	const row = readObject(value);
	if (
		Object.keys(row).sort().join() !==
			"index_leaf_size,max_bounds_checks,max_module_steps,max_ray_face_checks,max_samples" ||
		Object.values(row).some(
			(n) => typeof n !== "number" || !Number.isSafeInteger(n) || n <= 0,
		)
	)
		throw new ApiError(502, "invalid_geometric_pv_limits");
	return row as unknown as GeometricPvLimits;
}
