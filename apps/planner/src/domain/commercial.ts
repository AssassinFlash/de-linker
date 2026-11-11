import type { JsonObject } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";

/**
 * The commercial sizing request, as the planner sends it. The engine sizes
 * commercial storage only from a 15-minute load profile plus the peak to hold
 * (services/engine/src/linker_engine/commercial.py `design()`); without both
 * it returns indicative ranges by design, so this module never presents a
 * request without them as a sizing.
 */
export interface CommercialSizing extends JsonObject {
	readonly plz: string;
	readonly grid_connection_kva: number;
	readonly annual_kwh: number;
	readonly goals: readonly string[];
	readonly peak_kw: number | null;
	readonly target_peak_kw: number | null;
	readonly pv_kwp: number | null;
	readonly backup_load_kw: number | null;
	readonly backup_hours: number | null;
	readonly load_profile_unit: "kW" | "kWh";
	readonly load_profile_csv?: string;
	readonly locale: "en" | "de";
}

/** The engine's own minimum: one week of 15-minute values. */
export const MINIMUM_PROFILE_INTERVALS = 96 * 7;

/** One interval of a load profile, in seconds. */
export const PROFILE_INTERVAL_SECONDS = 15 * 60;

const GOALS = ["peak_shaving", "self_consumption", "backup"] as const;

const finite = (value: unknown): value is number =>
	typeof value === "number" && Number.isFinite(value);

const optional = (value: unknown, bound: number): number | null => {
	if (value === undefined || value === null) return null;
	return finite(value) && value > 0 && value <= bound ? value : null;
};

export function readSizing(value: unknown): CommercialSizing {
	const input = readObject(value);
	const plz = input.plz;
	const goals = input.goals;
	if (
		typeof plz !== "string" ||
		!/^\d{5}$/.test(plz) ||
		!finite(input.grid_connection_kva) ||
		!finite(input.annual_kwh) ||
		!Array.isArray(goals) ||
		!goals.length ||
		!goals.every((goal) =>
			(GOALS as readonly string[]).includes(String(goal)),
		) ||
		!["kW", "kWh"].includes(String(input.load_profile_unit ?? "kW"))
	)
		throw new ApiError(422, "invalid_commercial_sizing");
	// Built field by field: the browser never widens the engine's contract.
	return {
		plz,
		grid_connection_kva: input.grid_connection_kva,
		annual_kwh: input.annual_kwh,
		goals: goals as readonly string[],
		peak_kw: optional(input.peak_kw, 10000),
		target_peak_kw: optional(input.target_peak_kw, 10000),
		pv_kwp: optional(input.pv_kwp, 10000),
		backup_load_kw: optional(input.backup_load_kw, 10000),
		backup_hours: optional(input.backup_hours, 72),
		load_profile_unit: input.load_profile_unit === "kWh" ? "kWh" : "kW",
		locale: input.locale === "de" ? "de" : "en",
		...(typeof input.load_profile_csv === "string"
			? { load_profile_csv: input.load_profile_csv }
			: {}),
	};
}

/** The engine reads a semicolon file as semicolon-separated when it has them. */
function delimiterOf(text: string): string {
	const sample = text.slice(0, 2048);
	const semicolons = sample.split(";").length - 1;
	const commas = sample.split(",").length - 1;
	if (semicolons && semicolons >= commas) return ";";
	return sample.includes("\t") ? "\t" : ",";
}

/** A cell the engine would read as a number, in either decimal notation. */
function numeric(cell: string): number | null {
	const text = cell.trim().replace(/ /g, "");
	if (!text) return null;
	let normalized = text;
	if (text.includes(",") && text.includes("."))
		normalized =
			text.lastIndexOf(",") > text.lastIndexOf(".")
				? text.replace(/\./g, "").replace(",", ".")
				: text.replace(/,/g, "");
	else if (text.includes(",")) normalized = text.replace(",", ".");
	return /^-?\d+(?:\.\d+)?$/.test(normalized) ? Number(normalized) : null;
}

export interface ProfileRow {
	readonly value: number;
	/** The row's own timestamp cell, when it carries one. */
	readonly timestamp: string | null;
}

const TIMESTAMP = /\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/;

/**
 * The rows the engine will count: the last numeric cell of each row, skipping
 * headers and blank lines exactly as `parse_load_profile` does.
 */
export function profileRows(text: string): readonly ProfileRow[] {
	const delimiter = delimiterOf(text);
	const rows: ProfileRow[] = [];
	for (const line of text.replace(/\r\n?/g, "\n").split("\n")) {
		const cells = line.split(delimiter);
		let value: number | null = null;
		for (let index = cells.length - 1; index >= 0; index -= 1) {
			value = numeric(cells[index]!);
			if (value !== null) break;
		}
		if (value === null) continue;
		const stamp = cells.find((cell) => TIMESTAMP.test(cell));
		rows.push({ value, timestamp: stamp === undefined ? null : stamp.trim() });
	}
	return rows;
}

/** An instant only when the text says which instant it is. */
function instant(text: string): number | null {
	const trimmed = text.trim().replace(" ", "T");
	if (!/(?:Z|[+-]\d{2}:?\d{2})$/i.test(trimmed)) return null;
	const parsed = Date.parse(trimmed);
	return Number.isFinite(parsed) ? parsed : null;
}

export type ProfileRefusal =
	| "profile_empty"
	| "profile_too_short"
	| "profile_negative"
	| "profile_timestamps_need_offset"
	| "profile_irregular_intervals";

/**
 * Everything the interface can tell the customer before the request is sent.
 *
 * A profile that carries timestamps must say which instants they are: across a
 * daylight-saving change a local wall-clock hour repeats or is skipped, and a
 * profile read as one uniform 15-minute series would then silently shift by an
 * hour. Explicit UTC offsets (or Z) keep the series unambiguous, which is the
 * documented import contract.
 */
export function profileRefusal(
	rows: readonly ProfileRow[],
): ProfileRefusal | null {
	if (!rows.length) return "profile_empty";
	if (rows.length < MINIMUM_PROFILE_INTERVALS) return "profile_too_short";
	if (rows.some((row) => row.value < 0)) return "profile_negative";
	const stamped = rows.filter((row) => row.timestamp !== null);
	if (stamped.length) {
		const instants = stamped.map((row) =>
			row.timestamp === null ? null : instant(row.timestamp),
		);
		if (instants.some((value) => value === null))
			return "profile_timestamps_need_offset";
		for (let index = 1; index < instants.length; index += 1) {
			const step = instants[index]! - instants[index - 1]!;
			if (step <= 0 || step % (PROFILE_INTERVAL_SECONDS * 1000) !== 0)
				return "profile_irregular_intervals";
		}
	}
	return null;
}

/** The line the engine's own parser reads, so a rounded value stays rounded. */
export function profileCsv(rows: readonly ProfileRow[]): string {
	return rows.map((row) => String(row.value)).join("\n");
}
