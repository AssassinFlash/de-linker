import Ajv2020 from "ajv/dist/2020.js";
import importSchema from "../contracts/profile-import.schema.json" with { type: "json" };
import selectionSchema from "../contracts/profile-selections.schema.json" with { type: "json" };
import { ApiError } from "../data/protocol.ts";
import type { JsonObject } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";

export const MEASUREMENTS = [
	"gross_load",
	"critical_load",
	"net_import",
	"pv_available_ac",
	"pv_generation_ac",
	"aux_ac",
] as const;
export type Measurement = (typeof MEASUREMENTS)[number];
export type ProfileRole = Measurement | "pv_reference";
export interface CsvMapping extends JsonObject {
	readonly timestamp_column: string;
	readonly value_column: string;
	readonly measurement: Measurement;
	readonly value_kind: "interval_average_kw" | "interval_energy_kwh";
	readonly timestamp_role: "start" | "end";
	readonly timezone: string;
	readonly origin: "measured" | "modelled" | "template" | "synthetic";
	readonly interval_seconds: number | null;
	readonly delimiter: string;
	readonly decimal: "." | ",";
	readonly end_timestamp_column: string | null;
	readonly fold_column: string | null;
	readonly end_fold_column: string | null;
	readonly offset_rule: "explicit_offset_precedes_naive_timezone";
	readonly within_interval_assumption: "constant_mean_no_new_observations";
}
export interface ImportCommand extends JsonObject {
	readonly schema_version: 1;
	readonly project_id: string;
	readonly content_base64: string;
	readonly mapping: CsvMapping;
	readonly source_label: string;
	readonly rights_note: string;
	readonly key: string;
}
export interface ProfileSelections extends JsonObject {
	readonly schema_version: 1;
	readonly selected: Readonly<Partial<Record<ProfileRole, string>>>;
}
export interface ProfileAsset extends JsonObject {
	readonly id: string;
	readonly project_id: string;
	readonly content_sha256: string;
	readonly metadata_sha256: string;
	readonly media_type: string;
	readonly purpose:
		| "csv_profile_v1"
		| "pvgis_system_profile_v1"
		| "pvlib_reference_profile_v1"
		| "geometric_pv_reference_profile_v1"
		| "pvgis_roof_ac_reference_profile_v1";
	readonly metadata: JsonObject;
}
export interface CsvInspection {
	readonly content_sha256: string;
	readonly delimiter: string;
	readonly columns: readonly string[];
	readonly record_count: number;
	readonly rows: readonly {
		readonly line: number;
		readonly cells: readonly string[];
	}[];
	readonly rows_truncated: boolean;
}
export interface ProfilePreview {
	readonly project_id: string;
	readonly asset_id: string;
	readonly content_sha256: string;
	readonly metadata_sha256: string;
	readonly measurement: Measurement;
	readonly source: JsonObject;
	readonly transformations: readonly JsonObject[];
	readonly summary: {
		readonly start_utc: string;
		readonly end_utc: string;
		readonly interval_count: number;
		readonly covered_seconds: number;
		readonly span_seconds: number;
		readonly gap_seconds: number;
		readonly gap_count: number;
		readonly energy_kwh: number;
		readonly min_interval_mean_kw: number;
		readonly max_interval_mean_kw: number;
		readonly native_max_interval_seconds: number;
		readonly effective_max_interval_seconds: number;
		readonly reconstructed_means: boolean;
	};
	readonly rows: readonly {
		readonly interval_index: number;
		readonly start_utc: string;
		readonly end_utc: string;
		readonly interval_mean_kw: number;
	}[];
	readonly first_gaps: readonly {
		readonly start_utc: string;
		readonly end_utc: string;
	}[];
	readonly gaps_truncated: boolean;
	readonly next_offset: number | null;
}
const ajv = new Ajv2020({
	strict: true,
	strictNumbers: true,
	allErrors: false,
});
const checkImport = ajv.compile<ImportCommand>(importSchema);
const checkSelections = ajv.compile<ProfileSelections>(selectionSchema);
export function readImport(value: unknown): ImportCommand {
	readObject(value);
	if (!checkImport(value)) throw new ApiError(422, "invalid_profile_import");
	return value;
}
export function readSelections(value: unknown): ProfileSelections {
	if (value === undefined) return { schema_version: 1, selected: {} };
	if (!checkSelections(value))
		throw new ApiError(422, "invalid_profile_selections");
	return value;
}
const id = (value: unknown) =>
	typeof value === "string" && /^[a-f0-9]{32}$/.test(value);
const hash = (value: unknown) =>
	typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
const count = (value: unknown) =>
	typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
const number = (value: unknown) =>
	typeof value === "number" && Number.isFinite(value);
const instant = (value: unknown) =>
	typeof value === "string" &&
	/(?:Z|\+00:00)$/.test(value) &&
	Number.isFinite(Date.parse(value));
export function readAsset(value: unknown, projectId: string): ProfileAsset {
	const item = readObject(value);
	if (
		!id(item.id) ||
		item.project_id !== projectId ||
		!hash(item.content_sha256) ||
		!hash(item.metadata_sha256) ||
		typeof item.media_type !== "string" ||
		![
			"csv_profile_v1",
			"pvgis_system_profile_v1",
			"pvlib_reference_profile_v1",
			"geometric_pv_reference_profile_v1",
			"pvgis_roof_ac_reference_profile_v1",
		].includes(String(item.purpose))
	)
		throw new ApiError(502, "invalid_profile_reply");
	readObject(item.metadata);
	return item as ProfileAsset;
}
export function readInspection(
	value: unknown,
	delimiter: string,
): CsvInspection {
	const item = readObject(value);
	if (
		item.schema_version !== 1 ||
		item.evaluation_scope !== "csv_structure_only" ||
		!hash(item.content_sha256) ||
		item.delimiter !== delimiter ||
		!Array.isArray(item.columns) ||
		!item.columns.length ||
		item.columns.some((cell) => typeof cell !== "string") ||
		!count(item.record_count) ||
		item.record_count === 0 ||
		typeof item.rows_truncated !== "boolean" ||
		!Array.isArray(item.rows)
	)
		throw new ApiError(502, "invalid_profile_reply");
	for (const row of item.rows) {
		const record = readObject(row);
		if (
			!count(record.line) ||
			record.line === 0 ||
			!Array.isArray(record.cells) ||
			record.cells.length !== item.columns.length ||
			record.cells.some((cell) => typeof cell !== "string")
		)
			throw new ApiError(502, "invalid_profile_reply");
	}
	return item as unknown as CsvInspection;
}
export function readPreview(
	value: unknown,
	asset: ProfileAsset,
): ProfilePreview {
	const item = readObject(value);
	if (
		item.schema_version !== 1 ||
		item.evaluation_scope !== "profile_interpretation" ||
		item.project_id !== asset.project_id ||
		item.asset_id !== asset.id ||
		item.content_sha256 !== asset.content_sha256 ||
		item.metadata_sha256 !== asset.metadata_sha256 ||
		!(MEASUREMENTS as readonly unknown[]).includes(item.measurement)
	)
		throw new ApiError(502, "invalid_profile_reply");
	readObject(item.source);
	if (!Array.isArray(item.transformations))
		throw new ApiError(502, "invalid_profile_reply");
	item.transformations.forEach((value) => readObject(value));
	const summary = readObject(item.summary);
	if (
		!instant(summary.start_utc) ||
		!instant(summary.end_utc) ||
		typeof summary.reconstructed_means !== "boolean"
	)
		throw new ApiError(502, "invalid_profile_reply");
	for (const key of ["interval_count", "gap_count"])
		if (!count(summary[key])) throw new ApiError(502, "invalid_profile_reply");
	for (const key of [
		"covered_seconds",
		"span_seconds",
		"gap_seconds",
		"native_max_interval_seconds",
		"effective_max_interval_seconds",
	])
		if (!number(summary[key]) || (summary[key] as number) < 0)
			throw new ApiError(502, "invalid_profile_reply");
	for (const key of [
		"energy_kwh",
		"min_interval_mean_kw",
		"max_interval_mean_kw",
	])
		if (!number(summary[key])) throw new ApiError(502, "invalid_profile_reply");
	if (
		!Array.isArray(item.rows) ||
		!Array.isArray(item.first_gaps) ||
		typeof item.gaps_truncated !== "boolean" ||
		(item.next_offset !== null && !count(item.next_offset))
	)
		throw new ApiError(502, "invalid_profile_reply");
	for (const row of item.rows) {
		const record = readObject(row);
		if (
			!count(record.interval_index) ||
			!instant(record.start_utc) ||
			!instant(record.end_utc) ||
			!number(record.interval_mean_kw)
		)
			throw new ApiError(502, "invalid_profile_reply");
	}
	for (const gap of item.first_gaps) {
		const record = readObject(gap);
		if (
			!instant(record.start_utc) ||
			!instant(record.end_utc) ||
			Date.parse(String(record.end_utc)) <= Date.parse(String(record.start_utc))
		)
			throw new ApiError(502, "invalid_profile_reply");
	}
	return item as unknown as ProfilePreview;
}

/** Raw bytes are retained unchanged; the filename never enters provenance. */
export async function fileBase64(
	file: File,
	maxBytes: number,
): Promise<string> {
	if (file.size === 0 || file.size > maxBytes)
		throw new ApiError(413, "file_size");
	const bytes = new Uint8Array(await file.arrayBuffer());
	if (bytes.byteLength !== file.size || bytes.byteLength > maxBytes)
		throw new ApiError(413, "file_size");
	let binary = "";
	// Chunk size is a JS-call resource bound, not a time-series resolution.
	for (let offset = 0; offset < bytes.length; offset += 8192)
		binary += String.fromCharCode(...bytes.subarray(offset, offset + 8192));
	return btoa(binary);
}
