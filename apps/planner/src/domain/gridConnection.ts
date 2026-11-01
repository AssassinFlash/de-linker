import Ajv2020 from "ajv/dist/2020.js";
import schema from "../contracts/grid-connection.schema.json" with { type: "json" };
import { ApiError, type JsonObject } from "../data/protocol.ts";

export interface GridConnection extends JsonObject {
	schema_version: 1;
	dso_name: string | null;
	dso_source_url: string | null;
	voltage_level: "low" | "medium" | "high" | null;
	tab: {
		title: string | null;
		source_url: string | null;
		edition: string | null;
		date: string | null;
	};
}
const validate = new Ajv2020({
	strict: true,
	strictNumbers: true,
}).compile<GridConnection>(schema);
export function publicSourceUrl(value: string): boolean {
	try {
		const url = new URL(value);
		return (
			/^https?:\/\//i.test(value) &&
			!/^https?:\/\/[^/?#]*@/i.test(value) &&
			!!url.hostname &&
			!url.username &&
			!url.password &&
			!/\s/.test(value)
		);
	} catch {
		return false;
	}
}
export function calendarDate(value: string): boolean {
	const [year, month, day] = value.split("-").map(Number);
	const date = new Date(value + "T00:00:00Z");
	return (
		(year ?? 0) > 0 &&
		date.getUTCFullYear() === year &&
		date.getUTCMonth() + 1 === month &&
		date.getUTCDate() === day
	);
}
export function readGridConnection(value: unknown): GridConnection | undefined {
	if (value === undefined) return undefined;
	if (
		!validate(value) ||
		[value.dso_source_url, value.tab.source_url].some(
			(v) => v !== null && !publicSourceUrl(v),
		) ||
		(value.tab.date !== null && !calendarDate(value.tab.date))
	)
		throw new ApiError(422, "invalid_grid_connection");
	return value;
}
export function emptyGridConnection(): GridConnection {
	return {
		schema_version: 1,
		dso_name: null,
		dso_source_url: null,
		voltage_level: null,
		tab: { title: null, source_url: null, edition: null, date: null },
	};
}
export function replaceGridConnection(
	inputs: JsonObject,
	value: GridConnection | undefined,
): JsonObject {
	const { grid_connection: _removed, ...rest } = inputs;
	return value === undefined
		? rest
		: { ...rest, grid_connection: readGridConnection(value)! };
}
