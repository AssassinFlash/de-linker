/** Bounded owned source pages. Provider originals are never parsed in the browser. */
import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
export interface BeamWeatherAsset {
	readonly asset_id: string;
	readonly content_sha256: string;
	readonly metadata_sha256: string;
	readonly label: string;
	readonly synthetic_year: number;
	readonly interval_count: number;
}
export interface BeamWeatherRow {
	readonly source_row_index: number;
	readonly interval_start_utc: string;
	readonly interval_end_utc: string;
	readonly source_label_utc: string;
	readonly irradiance_at_utc: string;
}
export interface BeamWeatherSource {
	readonly start_year: number;
	readonly end_year: number;
	readonly radiation_database: string;
	readonly meteo_database: string;
	readonly irradiance_time_offset_hours: number;
	readonly months_selected: readonly { month: number; year: number }[];
	readonly weather_kind: "stitched_typical_months_not_observed_historical_year";
}
export const beamInteger = (n: unknown): n is number =>
	typeof n === "number" && Number.isSafeInteger(n) && n >= 0;
export const beamHash = (n: unknown): n is string =>
	typeof n === "string" && /^[a-f0-9]{64}$/.test(n);
export const beamId = (n: unknown): n is string =>
	typeof n === "string" && /^[a-f0-9]{32}$/.test(n);
export const beamUtc = (n: unknown): n is string =>
	typeof n === "string" &&
	/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|\+00:00)$/.test(n) &&
	Number.isFinite(Date.parse(n));
export function requireBeam(value: unknown): asserts value {
	if (!value) throw new ApiError(502, "invalid_direct_beam_reply");
}
function asset(value: unknown): BeamWeatherAsset {
	const row = readObject(value);
	requireBeam(
		beamId(row.asset_id) &&
			beamHash(row.content_sha256) &&
			beamHash(row.metadata_sha256) &&
			typeof row.label === "string" &&
			row.label.trim() &&
			beamInteger(row.synthetic_year) &&
			row.synthetic_year > 0 &&
			beamInteger(row.interval_count) &&
			row.interval_count > 0,
	);
	return row as unknown as BeamWeatherAsset;
}
export function readBeamWeatherAssets(
	value: unknown,
	projectId: string,
	offset: number,
	pageSize: number,
) {
	const row = readObject(value);
	requireBeam(
		row.schema_version === 1 &&
			row.project_id === projectId &&
			row.offset === offset &&
			Array.isArray(row.assets) &&
			row.assets.length <= pageSize &&
			(row.next_offset === null ||
				(beamInteger(row.next_offset) && row.next_offset > offset)),
	);
	const assets = (row.assets as readonly unknown[]).map(asset);
	requireBeam(new Set(assets.map((a) => a.asset_id)).size === assets.length);
	return { assets, next: row.next_offset as number | null };
}
export function readBeamWeatherPreview(
	value: unknown,
	projectId: string,
	selected: BeamWeatherAsset,
	offset: number,
	pageSize: number,
) {
	const row = readObject(value),
		source = readObject(row.source);
	requireBeam(
		row.schema_version === 1 &&
			row.project_id === projectId &&
			row.asset_id === selected.asset_id &&
			row.content_sha256 === selected.content_sha256 &&
			row.metadata_sha256 === selected.metadata_sha256 &&
			row.synthetic_year === selected.synthetic_year &&
			beamHash(row.weather_document_sha256) &&
			row.offset === offset &&
			Array.isArray(row.rows) &&
			row.rows.length <= pageSize &&
			(row.next_offset === null ||
				(beamInteger(row.next_offset) &&
					row.next_offset > offset &&
					row.next_offset < selected.interval_count)),
	);
	requireBeam(
		beamInteger(source.start_year) &&
			beamInteger(source.end_year) &&
			source.end_year >= source.start_year &&
			typeof source.radiation_database === "string" &&
			typeof source.meteo_database === "string" &&
			typeof source.irradiance_time_offset_hours === "number" &&
			Number.isFinite(source.irradiance_time_offset_hours) &&
			source.weather_kind ===
				"stitched_typical_months_not_observed_historical_year" &&
			Array.isArray(source.months_selected),
	);
	const rows = (row.rows as readonly unknown[]).map((value, i) => {
		const item = readObject(value);
		requireBeam(
			item.source_row_index === offset + i &&
				Number(item.source_row_index) < selected.interval_count &&
				beamUtc(item.interval_start_utc) &&
				beamUtc(item.interval_end_utc) &&
				Date.parse(item.interval_end_utc) >
					Date.parse(item.interval_start_utc) &&
				beamUtc(item.source_label_utc) &&
				beamUtc(item.irradiance_at_utc),
		);
		return item as unknown as BeamWeatherRow;
	});
	return {
		rows,
		source: source as unknown as BeamWeatherSource,
		next: row.next_offset as number | null,
		weatherDocumentSha256: row.weather_document_sha256 as string,
	};
}
