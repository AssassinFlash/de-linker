import type { JsonObject } from "./protocol.ts";
import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import { sameJson } from "../domain/draft.ts";
import {
	PVGIS_REFERENCE_TASK,
	PVGIS_REFERENCE_PURPOSE,
} from "../domain/pvgisReference.ts";
import {
	GEOMETRIC_PV_MODEL,
	GEOMETRIC_PV_PURPOSE,
	GEOMETRIC_PV_TASK,
} from "../domain/geometricPv.ts";

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
	kind:
		| typeof WEATHER_TASK
		| typeof PV_TASK
		| typeof PVGIS_REFERENCE_TASK
		| typeof GEOMETRIC_PV_TASK,
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
			pinned.runtime_bundle === context.code_sha256 &&
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
			hash(pinned["weather_acquisition.plan"]) &&
				hash(children.acquisition_plan) &&
				dependencies.acquisition_plan === pinned["weather_acquisition.plan"] &&
				dependencies.runtime_bundle === pinned.runtime_bundle &&
				dependencies.weather_original === asset.content_sha256 &&
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
	} else if (kind === PVGIS_REFERENCE_TASK) {
		const summary = readObject(result.profile_summary),
			start =
				typeof summary.start_utc === "string"
					? new Date(summary.start_utc)
					: null,
			end =
				typeof summary.end_utc === "string" ? new Date(summary.end_utc) : null;
		const keys = Object.keys(children),
			fixed = [
				"reference_plan",
				"reference_geometry",
				"reference_parameters",
				"reference_woo_module",
				"reference_output",
			],
			originals = keys.filter((key) => /^array\.\d+\.original$/.test(key));
		require(
			asset.purpose === PVGIS_REFERENCE_PURPOSE &&
				metadata.profile_type === asset.purpose &&
				metadata.derived_from_revision === run.revision &&
				hash(metadata.geometry_sha256) &&
				hash(metadata.parameters_sha256) &&
				metadata.geometry_sha256 === children.reference_geometry &&
				metadata.parameters_sha256 === children.reference_parameters &&
				pinned["pvgis_reference.plan"] === children.reference_plan &&
				pinned["woo.module_inputs"] === children.reference_woo_module &&
				fixed.every((key) => hash(children[key])) &&
				originals.length > 0 &&
				keys.length === fixed.length + originals.length * 2 &&
				originals.every(
					(_, index) =>
						hash(children[`array.${index}.original`]) &&
						hash(children[`array.${index}.capture`]),
				) &&
				sameJson(summary, metadata.interpretation) &&
				summary.measurement === "pv_available_ac" &&
				summary.origin === "modelled" &&
				summary.model_role === "official_calendar_year_roof_ac_reference" &&
				summary.native_max_interval_seconds === 3600 &&
				typeof summary.reconstructed_means === "boolean" &&
				finite(summary.energy_kwh) &&
				summary.energy_kwh >= 0 &&
				start &&
				end &&
				Number.isFinite(start.valueOf()) &&
				Number.isFinite(end.valueOf()) &&
				summary.start_utc ===
					`${start.getUTCFullYear().toString().padStart(4, "0")}-01-01T00:00:00+00:00` &&
				summary.end_utc ===
					`${(start.getUTCFullYear() + 1).toString().padStart(4, "0")}-01-01T00:00:00+00:00` &&
				summary.interval_count === (end.valueOf() - start.valueOf()) / 3600000,
		);
		readObject(metadata.woo_module_inputs);
		for (const role of [
			"equipment_release",
			"country_assessment",
			"near_shading_assessment",
		])
			require(readObject(result[role]).status === "not_assessed");
	} else if (kind === GEOMETRIC_PV_TASK) {
		const summary = readObject(result.profile_summary),
			scope = readObject(result.scope),
			weather = readObject(metadata.weather);
		require(
			result.model === GEOMETRIC_PV_MODEL &&
				models.generation === GEOMETRIC_PV_MODEL &&
				asset.purpose === GEOMETRIC_PV_PURPOSE &&
				metadata.profile_type === asset.purpose &&
				metadata.derived_from_revision === run.revision &&
				hash(metadata.geometry_sha256) &&
				metadata.parameters_sha256 === children["project.parameters"] &&
				Object.keys(children).sort().join() ===
					"model.inputs,model.witness,project.parameters,weather.metadata,weather.raw,woo.module_inputs" &&
				Object.values(children).every(hash) &&
				children["weather.raw"] === pinned["weather.raw"] &&
				children["weather.metadata"] === pinned["weather.metadata"] &&
				children["woo.module_inputs"] === pinned["woo.module_inputs"] &&
				sameJson(summary, metadata.interpretation) &&
				summary.measurement === "pv_available_ac" &&
				summary.origin === "modelled" &&
				summary.model_role ===
					"direct_only_geometry_uniform_module_reference_scenario" &&
				summary.reconstructed_means === true &&
				finite(summary.energy_kwh) &&
				summary.energy_kwh >= 0 &&
				Number.isSafeInteger(summary.interval_count) &&
				Number(summary.interval_count) > 0 &&
				summary.interval_count === weather.interval_count &&
				summary.start_utc === weather.start_utc &&
				summary.end_utc === weather.end_utc &&
				hash(weather.weather_document_sha256) &&
				typeof summary.start_utc === "string" &&
				Number.isFinite(Date.parse(summary.start_utc)) &&
				typeof summary.end_utc === "string" &&
				Date.parse(summary.end_utc) > Date.parse(summary.start_utc) &&
				scope.diffuse_policy ===
					"retain_unobstructed_sky_and_ground_components_v1" &&
				scope.thermal_policy === "sapm_from_module_mean_poa_v1" &&
				scope.electrical_policy ===
					"uniform_module_pvwatts_independent_mpp_sum_v1" &&
				readObject(result.near_shading_assessment).status ===
					"direct_only_scenario_not_complete_assessment",
		);
		for (const role of ["equipment_release", "country_assessment"])
			require(readObject(result[role]).status === "not_assessed");
	} else {
		const summary = readObject(result.profile_summary);
		require(
			hash(pinned["weather.metadata"]) &&
				hash(children.pv_model_inputs) &&
				hash(children.pv_model_witness) &&
				asset.content_sha256 === pinned["weather.raw"] &&
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
