import type { JsonObject } from "./protocol.ts";
import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import type { PlanningRun } from "./planningProtocol.ts";
import { runTask } from "./planningProtocol.ts";
import { PV_TASK } from "./readPreparationResult.ts";
import { GEOMETRIC_PV_TASK } from "../domain/geometricPv.ts";
import { sameJson } from "../domain/draft.ts";

/** The visible weather facts must describe the exact source used by this task. */
export function readPreparationWeather(
	value: unknown,
	run: PlanningRun,
): JsonObject {
	const asset = readObject(value),
		prepared = readObject(run.result?.prepared_asset),
		metadata = readObject(prepared.metadata),
		source = readObject(asset.metadata),
		pins = readObject(readObject(run.manifest.context).assets);
	if (
		asset.purpose !== "pvgis_tmy_weather_v1" ||
		asset.project_id !== run.project_id ||
		asset.media_type !== "application/json" ||
		source.retention !== "permanent" ||
		source.schema !== 1 ||
		([PV_TASK, GEOMETRIC_PV_TASK].includes(runTask(run) ?? "")
			? asset.content_sha256 !== pins["weather.raw"] ||
				asset.metadata_sha256 !== pins["weather.metadata"]
			: !sameJson(asset, prepared)) ||
		!sameJson(source.weather_request, metadata.weather_request) ||
		!sameJson(source.weather_interpretation, metadata.weather_interpretation)
	)
		throw new ApiError(502, "preparation_source_mismatch");
	const request = readObject(source.weather_request),
		weather = readObject(source.weather),
		details = readObject(readObject(weather.source).details),
		interpretation = readObject(source.weather_interpretation),
		provenance = readObject(source.provenance);
	if (
		typeof provenance.label !== "string" ||
		!provenance.label.trim() ||
		typeof details.radiation_database !== "string" ||
		typeof details.meteo_database !== "string" ||
		!sameJson(details.request, request) ||
		!sameJson(details.interpretation, interpretation) ||
		typeof request.api_version !== "string" ||
		!Number.isSafeInteger(request.start_year) ||
		!Number.isSafeInteger(request.end_year) ||
		Number(request.end_year) < Number(request.start_year) ||
		!Number.isSafeInteger(interpretation.synthetic_energy_year)
	)
		throw new ApiError(502, "preparation_source_mismatch");
	return source;
}
