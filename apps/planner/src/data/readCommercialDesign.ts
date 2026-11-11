import type { JsonObject } from "./protocol.ts";
import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";

/**
 * The engine's commercial design answer (`services/engine` `CommercialResult`).
 * `sized` carries the systems that reach the shaved power and energy; without
 * a profile and a target the engine answers `indicative` by design, and this
 * reader keeps that distinction instead of flattening it.
 */
export interface CommercialRange extends JsonObject {
	readonly low: number;
	readonly high: number;
}

export interface CommercialSystem extends JsonObject {
	readonly inverter: JsonObject;
	readonly inverter_units: number;
	readonly battery: JsonObject | null;
	readonly usable_kwh: number | null;
	readonly power_kw: number;
	readonly lines: readonly JsonObject[];
}

export interface CommercialLoad extends JsonObject {
	readonly intervals: number;
	readonly days: number;
	readonly annual_kwh: number;
	readonly peak_kw: number;
}

export interface CommercialOption extends JsonObject {
	readonly cap_kw: number;
	readonly power_kw: number;
	readonly energy_kwh: number;
	readonly events: number;
}

export interface CommercialDesign extends JsonObject {
	readonly status: "sized" | "indicative";
	readonly load: CommercialLoad | null;
	readonly options: readonly CommercialOption[];
	readonly power_kw_range: CommercialRange | null;
	readonly energy_kwh_range: CommercialRange | null;
	readonly basis: readonly string[];
	readonly systems: readonly CommercialSystem[];
	readonly warnings: readonly string[];
	readonly inquiry: string;
}

const finite = (value: unknown): value is number =>
	typeof value === "number" && Number.isFinite(value);

const range = (value: unknown): CommercialRange | null => {
	if (value === null || value === undefined) return null;
	const item = readObject(value);
	if (!finite(item.low) || !finite(item.high))
		throw new ApiError(502, "invalid_commercial_result");
	return { low: item.low, high: item.high };
};

const product = (value: unknown): JsonObject => {
	const item = readObject(value);
	if (
		!Number.isSafeInteger(item.id) ||
		typeof item.model !== "string" ||
		typeof item.sku !== "string"
	)
		throw new ApiError(502, "invalid_commercial_result");
	return item;
};

export function readCommercialDesign(value: unknown): CommercialDesign {
	const result = readObject(value);
	if (!["sized", "indicative"].includes(String(result.status)))
		throw new ApiError(502, "invalid_commercial_result");
	const load =
		result.load === null || result.load === undefined
			? null
			: readObject(result.load);
	if (
		load &&
		(!Number.isSafeInteger(load.intervals) ||
			!finite(load.days) ||
			!finite(load.annual_kwh) ||
			!finite(load.peak_kw))
	)
		throw new ApiError(502, "invalid_commercial_result");
	const options = result.options ?? [];
	const systems = result.systems ?? [];
	const basis = result.basis ?? [];
	const warnings = result.warnings ?? [];
	if (
		!Array.isArray(options) ||
		!Array.isArray(systems) ||
		!Array.isArray(basis) ||
		!Array.isArray(warnings) ||
		!basis.every((line) => typeof line === "string") ||
		!warnings.every((line) => typeof line === "string")
	)
		throw new ApiError(502, "invalid_commercial_result");
	const readOptions = options.map((value) => {
		const option = readObject(value);
		if (
			!finite(option.cap_kw) ||
			!finite(option.power_kw) ||
			!finite(option.energy_kwh) ||
			!Number.isSafeInteger(option.events)
		)
			throw new ApiError(502, "invalid_commercial_result");
		return option as CommercialOption;
	});
	const readSystems = systems.map((value) => {
		const system = readObject(value);
		if (
			!Number.isSafeInteger(system.inverter_units) ||
			!finite(system.power_kw) ||
			!Array.isArray(system.lines)
		)
			throw new ApiError(502, "invalid_commercial_result");
		system.lines.forEach((line) => readObject(line));
		const inverter = product(system.inverter);
		const battery =
			system.battery === null || system.battery === undefined
				? null
				: product(system.battery);
		return {
			...system,
			inverter,
			battery,
			usable_kwh: finite(system.usable_kwh) ? system.usable_kwh : null,
		} as CommercialSystem;
	});
	return {
		...result,
		status: result.status as "sized" | "indicative",
		load: load as CommercialLoad | null,
		options: readOptions,
		power_kw_range: range(result.power_kw_range),
		energy_kwh_range: range(result.energy_kwh_range),
		basis,
		systems: readSystems,
		warnings,
		inquiry: typeof result.inquiry === "string" ? result.inquiry : "",
	};
}
