import type { JsonObject } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";
import { entryInputs, readEntryHints } from "./entryHints.ts";
import type { EntryHints } from "./entryHints.ts";
import { readBrief } from "./brief.ts";

export interface SavedSolutionSource extends JsonObject {
	readonly schema_version: 1;
	readonly solution_id: number;
	readonly title: string;
	readonly kind: string;
	readonly input: JsonObject;
	readonly recorded_items: readonly JsonObject[];
	readonly source_sha256: string;
}

/** A URL identifies a private source; it never contains customer input values. */
export function savedSolutionId(params: URLSearchParams): number | null {
	if (params.has("project") || !params.has("saved_solution")) return null;
	const values = params.getAll("saved_solution");
	if (values.length !== 1 || !/^[1-9]\d*$/.test(values[0]!)) return 0;
	const value = Number(values[0]);
	return Number.isSafeInteger(value) ? value : 0;
}

export function readSavedSolutionSource(
	value: unknown,
	id: number,
): SavedSolutionSource {
	const data = readObject(value);
	if (
		data.schema_version !== 1 ||
		data.solution_id !== id ||
		typeof data.title !== "string" ||
		typeof data.kind !== "string" ||
		typeof data.source_sha256 !== "string" ||
		!/^[a-f0-9]{64}$/.test(data.source_sha256) ||
		!Array.isArray(data.recorded_items)
	)
		throw new ApiError(502, "invalid_saved_solution_source");
	readObject(data.input);
	for (const item of data.recorded_items) {
		const row = readObject(item);
		if (
			!Number.isSafeInteger(row.product_id) ||
			(row.product_id as number) <= 0 ||
			!Number.isSafeInteger(row.quantity) ||
			(row.quantity as number) <= 0 ||
			Object.keys(row).some((key) => key !== "product_id" && key !== "quantity")
		)
			throw new ApiError(502, "invalid_saved_solution_source");
	}
	return data as SavedSolutionSource;
}

export function savedSolutionHints(source: SavedSolutionSource): EntryHints {
	const empty: EntryHints = {
		annualKwh: null,
		pvKw: null,
		phase: null,
		backup: null,
		postalCode: null,
		roof: false,
		equipment: false,
		productId: null,
		invalid: true,
	};
	if (!["residential", "commercial"].includes(source.kind)) return empty;
	const params = new URLSearchParams();
	let unsupported = false;
	for (const key of ["annual_kwh", "pv_kwp", "phase", "backup", "plz"]) {
		const value = source.input[key];
		if (typeof value === "number" || typeof value === "string")
			params.set(key, String(value));
		else if (value !== null && value !== undefined) unsupported = true;
	}
	const hints = readEntryHints(params) ?? { ...empty, invalid: false };
	hints.invalid ||= unsupported;
	// The residential form's figure excluded additional heat-pump/EV demand.
	// Their absence must be explicit before carrying it as the gross annual total.
	if (
		source.kind === "residential" &&
		(source.input.heat_pump !== false ||
			source.input.electric_vehicle !== false)
	) {
		hints.annualKwh = null;
		if (source.input.annual_kwh !== undefined) hints.invalid = true;
	}
	const known = new Set([
		"locale",
		"annual_kwh",
		"pv_kwp",
		"phase",
		"backup",
		"plz",
		"heat_pump",
		"electric_vehicle",
	]);
	if (Object.keys(source.input).some((key) => !known.has(key)))
		hints.invalid = true;
	return hints;
}

/** Archived input bytes have no role in equipment permission or calculations. */
export function savedSolutionInputs(
	source: SavedSolutionSource,
	hints: EntryHints,
	sourceNote: string,
	accessoryNote: string,
): JsonObject {
	const inputs = entryInputs(hints, sourceNote, accessoryNote);
	const brief = readBrief(inputs.brief);
	return {
		...inputs,
		brief: {
			...brief,
			project_use:
				source.kind === "residential" || source.kind === "commercial"
					? source.kind
					: null,
		},
		saved_solution_reference: {
			schema_version: 1,
			authority: "historical_user_input",
			solution_id: source.solution_id,
			title: source.title,
			kind: source.kind,
			input: source.input,
			recorded_items: source.recorded_items,
			source_sha256: source.source_sha256,
		},
	};
}
