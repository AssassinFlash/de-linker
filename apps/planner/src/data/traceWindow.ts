import Ajv from "ajv";
import type { PlanningRun } from "./planningProtocol.ts";
import { ApiError } from "./protocol.ts";
import { runTask } from "./planningProtocol.ts";
import { DC_ENERGY_TASK } from "../domain/dcEnergy.ts";

export const TRACE_FIELDS = [
	"load_kw",
	"pv_kw",
	"charge_kw",
	"discharge_kw",
	"import_kw",
	"export_kw",
	"stored_kwh",
] as const;
export type TraceField = (typeof TRACE_FIELDS)[number];
export interface TraceRow extends Readonly<Record<TraceField, number>> {
	readonly interval_index: number;
	readonly start_utc: string;
	readonly end_utc: string;
}
export interface TraceWindow {
	readonly measurement_boundaries?: Readonly<Record<string, string>>;
	readonly schema_version: 1;
	readonly run_id: string;
	readonly manifest_sha256: string;
	readonly trace_sha256: string;
	readonly interval_count: number;
	readonly offset: number;
	readonly rows: readonly TraceRow[];
	readonly next_offset: number | null;
}
const object = (properties: Record<string, object>) => ({
	type: "object",
	properties,
	required: Object.keys(properties),
	additionalProperties: false,
});
const integer = {
	type: "integer",
	minimum: 0,
	maximum: Number.MAX_SAFE_INTEGER,
};
const hash = { type: "string", pattern: "^[a-f0-9]{64}$" };
const instant = {
	type: "string",
	pattern:
		"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\\.[0-9]{1,6})?(?:Z|\\+00:00)$",
};
const traceShape = object({
	schema_version: { const: 1, type: "integer" },
	run_id: { type: "string", pattern: "^[a-f0-9]{32}$" },
	manifest_sha256: hash,
	trace_sha256: hash,
	interval_count: { ...integer, minimum: 1 },
	offset: integer,
	next_offset: { anyOf: [integer, { type: "null" }] },
	measurement_boundaries: object({
		pv: { const: "PV_DC_bus", type: "string" },
		charge: { const: "battery_DC_terminal", type: "string" },
		discharge: { const: "battery_DC_terminal", type: "string" },
		import: { const: "grid_AC", type: "string" },
		export: { const: "grid_AC", type: "string" },
	}),
	rows: {
		type: "array",
		items: object({
			interval_index: integer,
			start_utc: instant,
			end_utc: instant,
			...Object.fromEntries(
				TRACE_FIELDS.map((field) => [field, { type: "number", minimum: 0 }]),
			),
		}),
	},
});
traceShape.required = traceShape.required.filter(
	(key) => key !== "measurement_boundaries",
);
const check = new Ajv({
	strict: true,
	strictNumbers: true,
}).compile<TraceWindow>(traceShape);
export function readTraceWindow(
	value: unknown,
	run: PlanningRun,
	offset: number,
	pageSize: number,
): TraceWindow {
	if (
		!check(value) ||
		(runTask(run) === DC_ENERGY_TASK) !== !!value.measurement_boundaries ||
		value.run_id !== run.id ||
		value.manifest_sha256 !== run.manifest_sha256 ||
		value.trace_sha256 !== run.result?.trace_sha256 ||
		value.interval_count !== run.result?.interval_count ||
		value.offset !== offset ||
		value.rows.length !==
			Math.max(0, Math.min(pageSize, value.interval_count - offset)) ||
		value.next_offset !==
			(offset + value.rows.length < value.interval_count
				? offset + value.rows.length
				: null)
	)
		throw new ApiError(502, "invalid_trace_window");
	value.rows.forEach((row, index) => {
		if (
			row.interval_index !== offset + index ||
			!Number.isFinite(Date.parse(row.start_utc)) ||
			!Number.isFinite(Date.parse(row.end_utc)) ||
			row.end_utc <= row.start_utc
		)
			throw new ApiError(502, "invalid_trace_window");
	});
	return value;
}

/** Locale-independent CSV numbers retain the stored values; every column names
 * its unit. Only the exact displayed rows are exported, never chart samples. */
export function traceCsv(page: TraceWindow, labels: readonly string[]): string {
	const quote = (value: string) => '"' + value.replaceAll('"', '""') + '"';
	return (
		[
			labels.map(quote).join(","),
			...page.rows.map((row) =>
				[
					row.start_utc,
					row.end_utc,
					...TRACE_FIELDS.map((field) => String(row[field])),
				]
					.map(quote)
					.join(","),
			),
		].join("\r\n") + "\r\n"
	);
}
