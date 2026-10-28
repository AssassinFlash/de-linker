/** Consume a geometric witness without reinterpreting it as generation or loss. */
import type { JsonObject } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import { sameJson } from "../domain/draft.ts";
import { DIRECT_BEAM_METHOD, DIRECT_BEAM_TASK } from "../domain/directBeam.ts";
import type { DirectBeamLimits } from "../domain/directBeam.ts";
import type { GeometryDocument } from "../domain/geometry.ts";
import { readGeometry } from "../domain/validateGeometry.ts";
import { panelPoses } from "../domain/panelPoses.ts";
import policy from "../contracts/geometry-policy.json" with { type: "json" };
import {
	beamHash,
	beamId,
	beamInteger,
	beamUtc,
	requireBeam,
} from "./directBeamWeather.ts";
import type { BeamWeatherRow } from "./directBeamWeather.ts";

export interface BeamGrid {
	readonly cells_per_edge: number;
	readonly sample_count: number;
	readonly visible_sample_count: number;
	readonly visible_fraction: number;
	readonly blocker_sample_counts: Readonly<Record<string, number>>;
}
export interface BeamModule {
	readonly module_id: string;
	readonly array_id: string;
	readonly roof_id: string;
	readonly status: "sampled" | "night" | "back_facing_or_tangent";
	readonly coarse: BeamGrid | null;
	readonly fine: BeamGrid | null;
	readonly observed_absolute_delta: number | null;
}
export interface BeamResultRow extends BeamWeatherRow {
	readonly modules: readonly BeamModule[];
}
export interface DirectBeamResult {
	readonly geometry: GeometryDocument;
	readonly rows: readonly BeamResultRow[];
	readonly sampling: {
		readonly coarse_cells_per_edge: number;
		readonly fine_cells_per_edge: number;
		readonly sample_count: number;
		readonly ray_face_checks: number;
		readonly bounds_checks: number;
	};
	readonly limits: DirectBeamLimits;
}
const fraction = (n: unknown): n is number =>
	typeof n === "number" && Number.isFinite(n) && n >= 0 && n <= 1;
export function readDirectBeamLimits(value: unknown): DirectBeamLimits {
	const row = readObject(value);
	requireBeam(
		Object.keys(row).sort().join() ===
			"index_leaf_size,max_bounds_checks,max_ray_face_checks,max_samples,max_selected_rows" &&
			Object.values(row).every((n) => beamInteger(n) && n > 0),
	);
	return row as unknown as DirectBeamLimits;
}
function grid(
	value: unknown,
	edge: number,
	blockers: ReadonlySet<string>,
): BeamGrid {
	const row = readObject(value),
		counts = readObject(row.blocker_sample_counts);
	requireBeam(
		row.cells_per_edge === edge &&
			row.sample_count === edge * edge &&
			beamInteger(row.visible_sample_count) &&
			row.visible_sample_count <= Number(row.sample_count) &&
			fraction(row.visible_fraction) &&
			Object.entries(counts).every(
				([id, n]) =>
					blockers.has(id) && beamInteger(n) && n <= Number(row.sample_count),
			),
	);
	return row as unknown as BeamGrid;
}
export function readDirectBeamResult(
	value: unknown,
	run: JsonObject,
	manifest: JsonObject,
): DirectBeamResult {
	const result = readObject(value),
		context = readObject(manifest.context),
		pinned = readObject(result.pinned_assets),
		deps = readObject(result.dependencies),
		witness = readObject(result.visibility),
		sources = readObject(witness.sources),
		selection = readObject(witness.owned_weather_selection),
		sampling = readObject(witness.sampling),
		parameters = readObject(context.parameters);
	const requiredPins = [
		"geometry",
		"runtime_bundle",
		"weather.metadata",
		"weather.raw",
		"woo.module_inputs",
	];
	requireBeam(
		Object.keys(pinned).sort().join() === requiredPins.join() &&
			Object.keys(deps).sort().join() ===
				[...requiredPins, "weather.document", "weather.selection"]
					.sort()
					.join() &&
			[
				"geometry_sha256",
				"woo_module_basis_sha256",
				"weather_asset_metadata_sha256",
				"weather_document_sha256",
				"weather_selection_sha256",
			].every((key) => beamHash(sources[key])),
	);
	requireBeam(
		run.state === "succeeded" &&
			beamHash(run.result_sha256) &&
			result.schema === 1 &&
			result.kind === DIRECT_BEAM_TASK &&
			readObject(context.models).task === DIRECT_BEAM_TASK &&
			result.project_id === run.project_id &&
			result.revision === run.revision &&
			result.input_sha256 === manifest.input_sha256 &&
			result.manifest_sha256 === run.manifest_sha256 &&
			result.runtime_sha256 === context.code_sha256 &&
			sameJson(pinned, context.assets) &&
			pinned.runtime_bundle === context.code_sha256 &&
			Object.values(pinned).every(beamHash) &&
			Object.values(deps).every(beamHash) &&
			Object.entries(pinned).every(([key, sha]) => deps[key] === sha) &&
			result.result_scope === "geometric_witness_not_a_profile_or_power_loss" &&
			result.prepared_asset === undefined,
	);
	requireBeam(
		witness.schema_version === 1 &&
			witness.kind === "geometric_direct_beam_visibility_v1" &&
			witness.method === DIRECT_BEAM_METHOD &&
			witness.publication_status === "geometry_witness_not_a_power_profile" &&
			sources.schema_version === 1 &&
			sources.project_id === run.project_id &&
			sources.project_revision === run.revision &&
			sources.geometry_sha256 === pinned.geometry &&
			sources.woo_module_basis_sha256 === pinned["woo.module_inputs"] &&
			sources.weather_asset_metadata_sha256 === pinned["weather.metadata"] &&
			sources.weather_document_sha256 === deps["weather.document"] &&
			sources.weather_selection_sha256 === deps["weather.selection"],
	);
	requireBeam(
		selection.schema_version === 1 &&
			selection.project_id === run.project_id &&
			selection.project_revision === run.revision &&
			beamId(selection.asset_id) &&
			selection.asset_metadata_sha256 ===
				sources.weather_asset_metadata_sha256 &&
			selection.weather_document_sha256 === sources.weather_document_sha256 &&
			Array.isArray(selection.row_indices) &&
			selection.row_indices.length > 0,
	);
	const limits = readDirectBeamLimits(witness.limits);
	requireBeam(
		sameJson(witness.limits, parameters.visibility_limits) &&
			beamInteger(sampling.coarse_cells_per_edge) &&
			sampling.coarse_cells_per_edge > 0 &&
			beamInteger(sampling.fine_cells_per_edge) &&
			sampling.fine_cells_per_edge > sampling.coarse_cells_per_edge &&
			sampling.method === "equal_area_midpoints" &&
			sampling.delta_interpretation ===
				"observed_resolution_difference_not_error_bound" &&
			beamInteger(sampling.sample_count) &&
			sampling.sample_count <= limits.max_samples &&
			beamInteger(sampling.ray_face_checks) &&
			sampling.ray_face_checks <= limits.max_ray_face_checks &&
			beamInteger(sampling.bounds_checks) &&
			sampling.bounds_checks <= limits.max_bounds_checks &&
			Array.isArray(witness.rows) &&
			witness.rows.length === selection.row_indices.length &&
			witness.rows.length <= limits.max_selected_rows,
	);
	const geometry = readGeometry(result.frozen_geometry, policy),
		poses = panelPoses(geometry).filter((p) => p.included),
		poseMap = new Map(poses.map((p) => [p.id, p]));
	const blockers = new Set([
		...geometry.roofs.map((r) => r.id),
		...geometry.obstacles.map((r) => r.id),
		...poses.map((p) => p.id),
	]);
	let previous = -1;
	const rows = (witness.rows as readonly unknown[]).map((value, i) => {
		const row = readObject(value);
		requireBeam(
			beamInteger(row.source_row_index) &&
				row.source_row_index > previous &&
				row.source_row_index ===
					(selection.row_indices as readonly unknown[])[i] &&
				beamUtc(row.interval_start_utc) &&
				beamUtc(row.interval_end_utc) &&
				Date.parse(row.interval_end_utc) > Date.parse(row.interval_start_utc) &&
				beamUtc(row.source_label_utc) &&
				beamUtc(row.irradiance_at_utc) &&
				Array.isArray(row.modules) &&
				row.modules.length === poses.length,
		);
		previous = row.source_row_index;
		const seen = new Set<string>();
		const modules = (row.modules as readonly unknown[]).map((value) => {
			const module = readObject(value),
				pose =
					typeof module.module_id === "string"
						? poseMap.get(module.module_id)
						: null;
			requireBeam(
				pose &&
					!seen.has(pose.id) &&
					module.array_id === pose.array_id &&
					module.roof_id === pose.roof_id,
			);
			seen.add(pose.id);
			if (module.status === "sampled") {
				grid(module.coarse, Number(sampling.coarse_cells_per_edge), blockers);
				grid(module.fine, Number(sampling.fine_cells_per_edge), blockers);
				requireBeam(fraction(module.observed_absolute_delta));
			} else
				requireBeam(
					["night", "back_facing_or_tangent"].includes(String(module.status)) &&
						module.coarse === null &&
						module.fine === null &&
						module.observed_absolute_delta === null,
				);
			return module as unknown as BeamModule;
		});
		return { ...row, modules } as unknown as BeamResultRow;
	});
	for (const key of [
		"equipment_release",
		"country_assessment",
		"near_shading_assessment",
	])
		requireBeam(readObject(result[key]).status === "not_assessed");
	return {
		geometry,
		rows,
		sampling: sampling as unknown as DirectBeamResult["sampling"],
		limits,
	};
}
