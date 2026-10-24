import type { JsonObject } from "./protocol.ts";
import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import { sameJson } from "../domain/draft.ts";

export const WEATHER_TASK = "acquire_pvgis_tmy_weather_v1";
export const PV_TASK = "prepare_roof_pv_reference_v1";
const hash = (v: unknown): v is string =>
	typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
const id = (v: unknown): v is string =>
	typeof v === "string" && /^[a-f0-9]{32}$/.test(v);
const finite = (v: unknown): v is number =>
	typeof v === "number" && Number.isFinite(v);
function require(value: unknown): asserts value {
	if (!value) throw new ApiError(502, "invalid_preparation_result");
}

/** Validate consumed source facts; numerical generation remains server-owned. */
export function readPreparationResult(
	value: unknown,
	run: JsonObject,
	manifest: JsonObject,
	kind: typeof WEATHER_TASK | typeof PV_TASK,
): JsonObject {
	const result = readObject(value),
		context = readObject(manifest.context),
		models = readObject(context.models),
		pinned = readObject(result.pinned_assets),
		dependencies = readObject(result.dependencies),
		asset = readObject(result.prepared_asset),
		metadata = readObject(asset.metadata);
	require(
		run.state === "succeeded" &&
			hash(run.result_sha256) &&
			result.schema === 1 &&
			result.kind === kind &&
			models.task === kind &&
			result.project_id === run.project_id &&
			result.revision === run.revision &&
			result.input_sha256 === manifest.input_sha256 &&
			result.manifest_sha256 === run.manifest_sha256 &&
			result.runtime_sha256 === context.code_sha256 &&
			sameJson(pinned, context.assets) &&
			Object.values(pinned).every(hash) &&
			Object.values(dependencies).every(hash) &&
			id(asset.id) &&
			asset.project_id === run.project_id &&
			asset.media_type === "application/json" &&
			hash(asset.content_sha256) &&
			hash(asset.metadata_sha256) &&
			dependencies.prepared_asset_content === asset.content_sha256 &&
			dependencies.prepared_asset_metadata === asset.metadata_sha256 &&
			metadata.retention === "permanent" &&
			metadata.schema === 1,
	);
	const children = readObject(metadata.dependencies);
	require(
		Object.entries(children).every(
			([name, sha]) => hash(sha) && dependencies[name] === sha,
		),
	);
	if (kind === WEATHER_TASK) {
		const summary = readObject(result.weather_summary);
		require(
			asset.purpose === "pvgis_tmy_weather_v1" &&
				metadata.source_type === asset.purpose &&
				sameJson(summary, metadata.weather) &&
				finite(summary.latitude_deg) &&
				summary.latitude_deg >= -90 &&
				summary.latitude_deg <= 90 &&
				finite(summary.longitude_deg) &&
				summary.longitude_deg >= -180 &&
				summary.longitude_deg <= 180 &&
				finite(summary.altitude_m) &&
				Number.isSafeInteger(summary.interval_count) &&
				Number(summary.interval_count) > 0 &&
				typeof result.acquisition_run_id === "string" &&
				/^[A-Za-z0-9]+$/.test(result.acquisition_run_id),
		);
		readObject(metadata.weather_request);
		readObject(metadata.weather_interpretation);
	} else {
		const summary = readObject(result.profile_summary);
		require(
			asset.purpose === "pvlib_reference_profile_v1" &&
				metadata.profile_type === asset.purpose &&
				metadata.derived_from_revision === run.revision &&
				hash(metadata.geometry_sha256) &&
				hash(metadata.parameters_sha256) &&
				sameJson(summary, metadata.interpretation) &&
				summary.measurement === "pv_available_ac" &&
				summary.origin === "modelled" &&
				summary.model_role === "unshaded_reference_scenario" &&
				summary.reconstructed_means === true &&
				finite(summary.energy_kwh) &&
				summary.energy_kwh >= 0 &&
				Number.isSafeInteger(summary.interval_count) &&
				Number(summary.interval_count) > 0 &&
				typeof summary.start_utc === "string" &&
				Number.isFinite(Date.parse(summary.start_utc)) &&
				typeof summary.end_utc === "string" &&
				Date.parse(summary.end_utc) > Date.parse(summary.start_utc),
		);
		for (const role of [
			"equipment_release",
			"country_assessment",
			"near_shading_assessment",
		])
			require(readObject(result[role]).status === "not_assessed");
	}
	return result;
}
