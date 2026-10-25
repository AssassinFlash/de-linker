import { ApiError, type JsonObject } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";

export const COMPARISON_MODEL = "frozen_energy_comparison_v1";
export const COMPARISON_CONDITIONS = [
	"site",
	"periods",
	"demand_sources",
	"pv_weather",
	"time_resolution",
	"operating_requirements",
	"starting_inventory",
	"terminal_requirement",
	"load_scope",
	"calculation_method",
	"scenario_constraints",
	"battery_temperature",
] as const;
export const COMPARISON_METRICS = [
	"load_demand",
	"solar_supply",
	"grid_import",
	"unserved_load",
	"pv_export",
	"stored_final",
	"pv_generation",
	"solar_share",
	"pv_use",
] as const;
export const COMPARISON_DIFFERENCES = [
	"storage_parameters",
	"equipment_selection",
	"pv_design",
	"dc_auxiliary",
] as const;
export interface ComparisonReference extends JsonObject {
	run_id: string;
	revision: number;
	coupling: "independent_ac" | "shared_dc";
	scenario_constraint_status: "satisfied" | "violated";
	equipment_status: string | null;
	equipment_models: readonly string[];
	source_note: string;
	usable_window_kwh: number;
	modules_per_stack: number | null;
	parallel_stacks: number | null;
}
export interface ComparisonMetric extends JsonObject {
	id: string;
	unit: "kWh" | "%";
	delta_unit: "kWh" | "pp";
	baseline: number | null;
	candidate: number | null;
	baseline_boundary: "ac" | "dc" | "storage";
	candidate_boundary: "ac" | "dc" | "storage";
	delta: number | null;
	delta_reason: string | null;
}
export interface EnergyComparison extends JsonObject {
	model: typeof COMPARISON_MODEL;
	project_id: string;
	baseline: ComparisonReference;
	candidate: ComparisonReference;
	conditions_aligned: boolean;
	conditions: readonly {
		id: string;
		status: "matched" | "different" | "unavailable";
	}[];
	differences: readonly { id: string; changed: boolean }[];
	metrics: readonly ComparisonMetric[];
}
export function comparisonPair(
	value: string | null,
): readonly [string, string] | null {
	if (!value || !/^[a-f0-9]{32},[a-f0-9]{32}$/.test(value)) return null;
	const [a, b] = value.split(",");
	return a !== b ? [a!, b!] : null;
}
export function readEnergyComparison(
	value: unknown,
	projectId: string,
	a: string,
	b: string,
): EnergyComparison {
	const x = readObject(value);
	const fail = () => {
		throw new ApiError(502, "invalid_energy_comparison");
	};
	const hash = (v: unknown, n = 64) =>
		typeof v === "string" && new RegExp(`^[a-f0-9]{${n}}$`).test(v);
	if (
		x.schema_version !== 1 ||
		x.model !== COMPARISON_MODEL ||
		x.project_id !== projectId ||
		a === b ||
		typeof x.conditions_aligned !== "boolean" ||
		x.equipment_release !== "not_established" ||
		x.country_release !== "not_assessed"
	)
		fail();
	for (const [side, id] of [
		["baseline", a],
		["candidate", b],
	] as const) {
		const ref = readObject(x[side]);
		if (
			ref.run_id !== id ||
			!hash(id, 32) ||
			!Number.isSafeInteger(ref.revision) ||
			Number(ref.revision) < 1 ||
			!["shared_dc", "independent_ac"].includes(String(ref.coupling)) ||
			!["satisfied", "violated"].includes(
				String(ref.scenario_constraint_status),
			) ||
			!Array.isArray(ref.equipment_models) ||
			!ref.equipment_models.every((v) => typeof v === "string") ||
			typeof ref.source_note !== "string"
		)
			fail();
		for (const key of [
			"manifest_sha256",
			"result_sha256",
			"input_sha256",
			"runtime_sha256",
			"numerical_basis_sha256",
		])
			if (!hash(ref[key])) fail();
		if (
			typeof ref.usable_window_kwh !== "number" ||
			!Number.isFinite(ref.usable_window_kwh) ||
			ref.usable_window_kwh < 0
		)
			fail();
		for (const key of ["modules_per_stack", "parallel_stacks"])
			if (
				ref[key] !== null &&
				(typeof ref[key] !== "number" ||
					!Number.isSafeInteger(ref[key]) ||
					Number(ref[key]) < 1)
			)
				fail();
	}
	function rows(key: string, identities: readonly string[]) {
		const list = x[key];
		if (!Array.isArray(list) || list.length !== identities.length)
			return fail();
		return list.map((row, index) => {
			const item = readObject(row);
			if (item.id !== identities[index]) fail();
			return item;
		});
	}
	const conditions = rows("conditions", COMPARISON_CONDITIONS);
	for (const c of conditions)
		if (!["matched", "different", "unavailable"].includes(String(c.status)))
			fail();
	if (x.conditions_aligned !== conditions.every((c) => c.status === "matched"))
		fail();
	for (const d of rows("differences", COMPARISON_DIFFERENCES))
		if (typeof d.changed !== "boolean") fail();
	for (const row of rows("metrics", COMPARISON_METRICS)) {
		if (
			!["kWh", "%"].includes(String(row.unit)) ||
			!["kWh", "pp"].includes(String(row.delta_unit))
		)
			fail();
		for (const side of ["baseline", "candidate"])
			if (
				row[side] !== null &&
				(typeof row[side] !== "number" || !Number.isFinite(row[side]))
			)
				fail();
		for (const key of ["baseline_boundary", "candidate_boundary"])
			if (!["ac", "dc", "storage"].includes(String(row[key]))) fail();
		const undefinedValue = row.baseline === null || row.candidate === null;
		const reason = undefinedValue
			? "undefined_metric"
			: row.baseline_boundary !== row.candidate_boundary
				? "measurement_boundaries_differ"
				: !x.conditions_aligned
					? "conditions_differ"
					: null;
		if (
			row.delta_reason !== reason ||
			(reason === null
				? typeof row.delta !== "number" || !Number.isFinite(row.delta)
				: row.delta !== null)
		)
			fail();
		for (const key of [
			"baseline_undefined_reason",
			"candidate_undefined_reason",
		])
			if (row[key] !== null && typeof row[key] !== "string") fail();
	}
	return x as EnergyComparison;
}
