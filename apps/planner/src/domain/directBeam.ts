/** Project selections for the geometric witness; no PV or electrical-loss scaling. */
import Ajv2020 from "ajv/dist/2020.js";
import schema from "../contracts/direct-beam.schema.json" with { type: "json" };
import type { JsonObject } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";
import { sameJson } from "./draft.ts";

export const DIRECT_BEAM_TASK = "prepare_direct_beam_visibility_v1";
export const DIRECT_BEAM_METHOD = "declared_opaque_ray_midpoint_uvn_v1";
export interface DirectBeamDraft extends JsonObject {
	readonly schema_version: 1;
	readonly weather_asset_id: string | null;
	readonly row_indices: readonly number[];
	readonly sampling: {
		readonly coarse_cells_per_edge: number | null;
		readonly fine_cells_per_edge: number | null;
	};
}
export interface DirectBeamLimits {
	readonly max_selected_rows: number;
	readonly max_samples: number;
	readonly max_ray_face_checks: number;
	readonly max_bounds_checks: number;
	readonly index_leaf_size: number;
}
const check = new Ajv2020({ strict: true, strictNumbers: true }).compile(
	schema,
);
export function readDirectBeam(value: unknown): DirectBeamDraft {
	const row = readObject(value);
	if (
		!check(row) ||
		Number(readObject(row.sampling).fine_cells_per_edge) <=
			Number(readObject(row.sampling).coarse_cells_per_edge) ||
		!Number.isSafeInteger(readObject(row.sampling).coarse_cells_per_edge) ||
		!Number.isSafeInteger(readObject(row.sampling).fine_cells_per_edge) ||
		!Array.isArray(row.row_indices) ||
		row.row_indices.some(
			(n, i, all) => !Number.isSafeInteger(n) || (i > 0 && n <= all[i - 1]!),
		)
	)
		throw new ApiError(422, "direct_beam_inputs_invalid");
	return row as DirectBeamDraft;
}
export function directBeamDraft(inputs: JsonObject): DirectBeamDraft {
	if (inputs.direct_beam_visibility === undefined)
		return {
			schema_version: 1,
			weather_asset_id: null,
			row_indices: [],
			sampling: { coarse_cells_per_edge: null, fine_cells_per_edge: null },
		};
	const row = readObject(inputs.direct_beam_visibility),
		sampling = readObject(row.sampling);
	if (
		row.schema_version !== 1 ||
		Object.keys(row).sort().join() !==
			"row_indices,sampling,schema_version,weather_asset_id" ||
		(row.weather_asset_id !== null &&
			(typeof row.weather_asset_id !== "string" ||
				!/^[a-f0-9]{32}$/.test(row.weather_asset_id))) ||
		!Array.isArray(row.row_indices) ||
		row.row_indices.some(
			(n) => typeof n !== "number" || !Number.isSafeInteger(n) || n < 0,
		) ||
		Object.keys(sampling).sort().join() !==
			"coarse_cells_per_edge,fine_cells_per_edge" ||
		Object.values(sampling).some(
			(n) => n !== null && (typeof n !== "number" || !Number.isFinite(n)),
		)
	)
		throw new ApiError(422, "direct_beam_inputs_invalid");
	return row as DirectBeamDraft;
}
export function compileDirectBeam(
	value: DirectBeamDraft,
	limits: DirectBeamLimits,
): JsonObject {
	const complete = readDirectBeam(value);
	if (
		complete.row_indices.length > limits.max_selected_rows ||
		complete.row_indices.some((n, i, all) => i > 0 && n <= all[i - 1]!)
	)
		throw new ApiError(422, "direct_beam_selection_limit");
	return complete;
}
export function directBeamPrepared(
	inputs: JsonObject,
	limits: DirectBeamLimits,
): boolean {
	try {
		return sameJson(
			compileDirectBeam(directBeamDraft(inputs), limits),
			inputs.direct_beam_visibility,
		);
	} catch {
		return false;
	}
}
