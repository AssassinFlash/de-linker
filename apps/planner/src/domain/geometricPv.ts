/** A separately named AC scenario; existing unshaded profiles keep their identity. */
import Ajv2020 from "ajv/dist/2020.js";
import schema from "../contracts/geometric-pv.schema.json" with { type: "json" };
import type { JsonObject, Session } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";
import type { PvDraft } from "./solarSetup.ts";
import { compilePv, emptyPv, readSolarSetup } from "./solarSetup.ts";
import { sameJson } from "./draft.ts";
import { invalidateEnergyReplay } from "./energyScenario.ts";

export const GEOMETRIC_PV_TASK = "prepare_geometric_pv_reference_v1";
export const GEOMETRIC_PV_PURPOSE = "geometric_pv_reference_profile_v1";
export const GEOMETRIC_PV_MODEL_V1 = "opaque_direct_uniform_pvlib_reference_v1";
export const GEOMETRIC_PV_DIFFUSE_V1 =
	"retain_unobstructed_sky_and_ground_components_v1";
export const GEOMETRIC_PV_MODEL =
	"opaque_perez_component_visibility_pvlib_reference_v1";
export const GEOMETRIC_PV_MODEL_SERIES =
	"opaque_perez_series_iv_forward_reference_v1";
export const GEOMETRIC_PV_SERIES_ELECTRICAL =
	"whole_module_forward_series_iv_single_string_per_tracker_v1";
export const GEOMETRIC_PV_DIFFUSE =
	"cosine_weighted_perez_component_visibility_v1";
export const GEOMETRIC_PV_ROLE_V1 =
	"direct_only_geometry_uniform_module_reference_scenario";
export const GEOMETRIC_PV_ROLE =
	"perez_component_visibility_uniform_module_reference_scenario";
export const GEOMETRIC_PV_SHADING_V1 =
	"direct_only_scenario_not_complete_assessment";
export const GEOMETRIC_PV_SHADING =
	"perez_component_visibility_not_complete_assessment";
export const GEOMETRIC_PV_RESULTS = [
	{
		model: GEOMETRIC_PV_MODEL_V1,
		role: GEOMETRIC_PV_ROLE_V1,
		diffuse: GEOMETRIC_PV_DIFFUSE_V1,
		shading: GEOMETRIC_PV_SHADING_V1,
	},
	{
		model: GEOMETRIC_PV_MODEL,
		role: GEOMETRIC_PV_ROLE,
		diffuse: GEOMETRIC_PV_DIFFUSE,
		shading: GEOMETRIC_PV_SHADING,
	},
	{
		model: GEOMETRIC_PV_MODEL_SERIES,
		role: "perez_component_visibility_forward_series_iv_reference_scenario",
		diffuse: GEOMETRIC_PV_DIFFUSE,
		shading: GEOMETRIC_PV_SHADING,
	},
] as const;
const GEOMETRIC_PV_PAIRS: Record<string, string> = {
	[GEOMETRIC_PV_MODEL_V1]: GEOMETRIC_PV_DIFFUSE_V1,
	[GEOMETRIC_PV_MODEL]: GEOMETRIC_PV_DIFFUSE,
	[GEOMETRIC_PV_MODEL_SERIES]: GEOMETRIC_PV_DIFFUSE,
};
export interface GeometricPvDraft extends JsonObject {
	readonly schema_version: 1;
	readonly model:
		| typeof GEOMETRIC_PV_MODEL
		| typeof GEOMETRIC_PV_MODEL_V1
		| typeof GEOMETRIC_PV_MODEL_SERIES;
	readonly weather_asset_id: string | null;
	readonly sampling: {
		readonly coarse_cells_per_edge: number | null;
		readonly fine_cells_per_edge: number | null;
	};
	readonly diffuse_policy:
		typeof GEOMETRIC_PV_DIFFUSE | typeof GEOMETRIC_PV_DIFFUSE_V1;
	readonly thermal_policy: "sapm_from_module_mean_poa_v1";
	readonly electrical_policy:
		| "uniform_module_pvwatts_independent_mpp_sum_v1"
		| typeof GEOMETRIC_PV_SERIES_ELECTRICAL;
	readonly parameters: PvDraft;
}
export interface GeometricPvLimits {
	readonly max_module_steps: number;
	readonly max_samples: number;
	readonly max_ray_face_checks: number;
	readonly max_bounds_checks: number;
	readonly index_leaf_size: number;
}
export type GeometricPvClearFlatRoofLimits = NonNullable<
	Session["runtime"]["limits"]["geometric_pv_clear_flat_roof"]
>;
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
		diffuse_policy: GEOMETRIC_PV_DIFFUSE,
		thermal_policy: "sapm_from_module_mean_poa_v1",
		electrical_policy: "uniform_module_pvwatts_independent_mpp_sum_v1",
		parameters,
	};
}
/** Hemisphere plus horizon-ring directions, then the fine panel grid. */
export function geometricDiffuseSampleUpperBound(
	modules: number,
	fine: number,
): number {
	return modules * fine * fine * (4 * fine * fine + 4 * fine);
}
export function geometricPvDraft(inputs: JsonObject): GeometricPvDraft {
	if (inputs.geometric_pv_preparation === undefined)
		return emptyGeometricPv(readSolarSetup(inputs).pv);
	const row = readObject(inputs.geometric_pv_preparation),
		sampling = readObject(row.sampling),
		constants = emptyGeometricPv();
	if (
		Object.keys(row).sort().join() !== Object.keys(constants).sort().join() ||
		GEOMETRIC_PV_PAIRS[String(row.model)] !== row.diffuse_policy ||
		row.schema_version !== constants.schema_version ||
		row.thermal_policy !== constants.thermal_policy ||
		row.electrical_policy !==
			(row.model === GEOMETRIC_PV_MODEL_SERIES
				? GEOMETRIC_PV_SERIES_ELECTRICAL
				: constants.electrical_policy) ||
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
			Number(value.sampling.coarse_cells_per_edge) ||
		GEOMETRIC_PV_PAIRS[value.model] !== value.diffuse_policy ||
		(value.model !== GEOMETRIC_PV_MODEL_V1 &&
			value.parameters.arrays.some((array) => array.transposition !== "perez"))
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

export function readGeometricPvClearFlatRoofLimits(
	value: unknown,
): GeometricPvClearFlatRoofLimits | null {
	if (value === undefined) return null;
	const row = readObject(value);
	if (
		Object.keys(row).sort().join() !==
			"max_module_steps,max_modules,max_samples,max_strings,max_weather_rows" ||
		Object.values(row).some(
			(n) => typeof n !== "number" || !Number.isSafeInteger(n) || n <= 0,
		)
	)
		throw new ApiError(502, "invalid_geometric_pv_limits");
	return row as unknown as GeometricPvClearFlatRoofLimits;
}
