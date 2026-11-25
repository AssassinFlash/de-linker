import Ajv2020 from "ajv/dist/2020.js";
import existingSystemSchema from "../contracts/existing-system.schema.json" with { type: "json" };
import declaredRequirementsSchema from "../contracts/declared-equipment-requirements.schema.json" with { type: "json" };
import type { JsonObject } from "./protocol.ts";
import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import { sameJson } from "../domain/draft.ts";
import { readEquipmentSelection } from "../domain/equipment.ts";
import type { EquipmentSelection } from "../domain/equipment.ts";
import { readEquipmentAssessment } from "./readEquipmentResult.ts";
import { readEquipmentPlant } from "../domain/equipmentPlant.ts";
import type { EquipmentPlant } from "../domain/equipmentPlant.ts";
import { matchesPlantSearch, readPlantSearch } from "../domain/plantSearch.ts";

export const SEARCH_TASK = "search_woo_equipment_v1";
export interface EquipmentDemandResult extends JsonObject {
	status: "satisfied" | "violated" | "unresolved";
	reason: string;
	metrics: JsonObject | null;
	equipment: JsonObject | null;
}
export interface BoundedDemandResult extends JsonObject {
	metrics?: never;
	equipment?: never;
	status: "bounded" | "violated" | "unresolved";
	reason: string;
	basis: "optimistic_full_initial_storage_lossless_upper_bound_not_dispatch";
	additional_pv_use_upper_kwh: number | null;
	peak_import_lower_bound_kw: number | null;
	missing_facts: string[];
	source_facts: JsonObject[];
}
export type CandidateDemandResult = EquipmentDemandResult | BoundedDemandResult;
interface CandidateMetadata extends JsonObject {
	id: string;
	status: "violated" | "unresolved" | "satisfied";
	assessment_sha256: string;
	violated_checks: number;
	unresolved_checks: number;
	nominal_ac_kw?: number | null;
	usable_energy_kwh?: number | null;
	demand?: CandidateDemandResult;
}
interface SingleCandidate extends CandidateMetadata {
	selection: EquipmentSelection;
}
interface PlantCandidate extends CandidateMetadata {
	plant: EquipmentPlant;
}
export type EquipmentCandidate = SingleCandidate | PlantCandidate;
export function isPlantCandidate(
	candidate: EquipmentCandidate,
): candidate is PlantCandidate {
	return candidate.plant !== undefined;
}
const hash = (v: unknown) => typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
const count = (v: unknown) =>
	typeof v === "number" && Number.isSafeInteger(v) && v >= 0;
const nonnegative = (v: unknown): v is number =>
	typeof v === "number" && Number.isFinite(v) && v >= 0;
const PROFILE_BOUNDS = "profile_physical_bounds_v1";
const BOUND_BASIS =
	"optimistic_full_initial_storage_lossless_upper_bound_not_dispatch";
const existingSystemValid = new Ajv2020({
	strict: true,
	strictNumbers: true,
}).compile<JsonObject>(existingSystemSchema);

const declaredValid = new Ajv2020({
	strict: true,
	strictNumbers: true,
}).compile<JsonObject>(declaredRequirementsSchema);
function readDeclaredRequirements(value: unknown): JsonObject {
	if (!declaredValid(value)) throw new ApiError(502, "invalid_run_result");
	return value;
}

export function readProfileBaseline(value: unknown) {
	const demand = readObject(value);
	const baseline = readObject(demand.baseline);
	if (
		demand.model !== PROFILE_BOUNDS ||
		![
			"self_consumption_with_reserve_v1",
			"peak_shaving_with_reserve_v1",
		].includes(String(demand.controller)) ||
		typeof demand.horizon_start_utc !== "string" ||
		typeof demand.horizon_end_utc !== "string" ||
		!Number.isFinite(Date.parse(demand.horizon_start_utc)) ||
		!Number.isFinite(Date.parse(demand.horizon_end_utc)) ||
		Date.parse(demand.horizon_start_utc) >=
			Date.parse(demand.horizon_end_utc) ||
		!count(demand.interval_count) ||
		demand.interval_count === 0 ||
		!nonnegative(baseline.load_kwh) ||
		![
			"pv_available_kwh",
			"direct_pv_use_kwh",
			"grid_import_kwh",
			"grid_export_kwh",
			"peak_grid_import_kw",
			"over_target_kwh",
		].every((key) => baseline[key] === null || nonnegative(baseline[key]))
	)
		throw new ApiError(502, "invalid_run_result");
	return { demand, baseline };
}

export function readRetainedInverter(value: unknown) {
	const result = readObject(value);
	if (
		!existingSystemValid(result.existing_system) ||
		result.existing_system.keep_inverter !== true
	)
		throw new ApiError(502, "invalid_run_result");
	const requirements = readDeclaredRequirements(result.requirements);
	const units = result.units === undefined ? [] : result.units;
	if (!Array.isArray(units)) throw new ApiError(502, "invalid_run_result");
	return {
		existing: result.existing_system,
		profile:
			result.profile_baseline === undefined
				? null
				: readProfileBaseline(result.profile_baseline),
		requirements,
		units: units.map((unit) => {
			const row = readObject(unit);
			if (typeof row.id !== "string" || typeof row.name !== "string")
				throw new ApiError(502, "invalid_run_result");
			return {
				id: row.id,
				name: row.name,
				requirements: readDeclaredRequirements(row.requirements),
			};
		}),
	};
}

export function readEquipmentSearchResult(
	value: unknown,
	run: JsonObject,
	manifest: JsonObject,
): JsonObject {
	const result = readObject(value),
		context = readObject(manifest.context),
		pinned = readObject(result.pinned_assets);
	if (
		result.schema !== 1 ||
		result.kind !== SEARCH_TASK ||
		result.project_id !== run.project_id ||
		result.revision !== run.revision ||
		result.input_sha256 !== manifest.input_sha256 ||
		result.manifest_sha256 !== run.manifest_sha256 ||
		result.runtime_sha256 !== context.code_sha256 ||
		!sameJson(pinned, context.assets)
	)
		throw new ApiError(502, "invalid_run_result");
	if (result.retained_inverter !== undefined) {
		if (
			result.search !== undefined ||
			result.assessment !== undefined ||
			pinned["woo.equipment_inputs"] !== undefined
		)
			throw new ApiError(502, "invalid_run_result");
		readRetainedInverter(result.retained_inverter);
		return result;
	}
	const search = readObject(result.search),
		coverage = readObject(search.coverage);
	if (
		!hash(pinned["woo.equipment_inputs"]) ||
		!["budget_exhausted", "exhausted_supported_domain"].includes(
			String(search.completion),
		) ||
		!count(search.work_used) ||
		!count(search.work_budget) ||
		search.work_budget === 0 ||
		(search.work_used as number) > (search.work_budget as number) ||
		!Array.isArray(search.candidates) ||
		!Array.isArray(search.products) ||
		![
			"one_converter_one_external_battery_assembly",
			"declared_plant_one_external_assembly_per_converter",
		].includes(String(coverage.template)) ||
		// Saved runs retain the ranking policy used for their assessment.
		![
			"unresolved_then_product_and_module_count",
			"dc_ac_proximity_then_unresolved_then_product_and_module_count",
			"not_performed_before_qualification",
		].includes(String(search.ranking))
	)
		throw new ApiError(502, "invalid_run_result");
	if (search.demand !== undefined) {
		const demand = readObject(search.demand);
		if (
			!["single_ac_equipment_demand_v1", PROFILE_BOUNDS].includes(
				String(demand.model),
			) ||
			!["complete", "budget_exhausted"].includes(String(demand.completion)) ||
			!count(demand.interval_count) ||
			!count(demand.work_used) ||
			!count(demand.work_budget) ||
			demand.work_budget === 0 ||
			(demand.work_used as number) > (demand.work_budget as number)
		)
			throw new ApiError(502, "invalid_run_result");
		if (demand.model === PROFILE_BOUNDS) readProfileBaseline(demand);
	}
	const ids = new Set<string>();
	let qualified = 0;
	for (const value of search.candidates) {
		const c = readObject(value);
		if (
			!hash(c.id) ||
			ids.has(String(c.id)) ||
			!hash(c.assessment_sha256) ||
			!["violated", "unresolved", "satisfied"].includes(String(c.status)) ||
			!count(c.violated_checks) ||
			!count(c.unresolved_checks) ||
			(c.nominal_ac_kw != null && !nonnegative(c.nominal_ac_kw)) ||
			(c.usable_energy_kwh !== undefined &&
				c.usable_energy_kwh !== null &&
				(typeof c.usable_energy_kwh !== "number" ||
					!Number.isFinite(c.usable_energy_kwh) ||
					c.usable_energy_kwh < 0))
		)
			throw new ApiError(502, "invalid_run_result");
		if (
			search.demand !== undefined &&
			readObject(search.demand).model === PROFILE_BOUNDS
		) {
			const demand = readObject(c.demand);
			if (
				!["bounded", "violated", "unresolved"].includes(
					String(demand.status),
				) ||
				typeof demand.reason !== "string" ||
				!demand.reason ||
				demand.basis !== BOUND_BASIS ||
				!Array.isArray(demand.missing_facts) ||
				!demand.missing_facts.every((v) => typeof v === "string") ||
				!Array.isArray(demand.source_facts)
			)
				throw new ApiError(502, "invalid_run_result");
			demand.source_facts.forEach((fact) => readObject(fact));
			for (const key of [
				"additional_pv_use_upper_kwh",
				"peak_import_lower_bound_kw",
			]) {
				if (demand[key] !== null && !nonnegative(demand[key]))
					throw new ApiError(502, "invalid_run_result");
			}
			const summary = readObject(search.demand),
				baseline = readObject(summary.baseline);
			if (
				demand.status !== "unresolved" &&
				(!nonnegative(demand.additional_pv_use_upper_kwh) ||
					(summary.controller === "peak_shaving_with_reserve_v1" &&
						!nonnegative(demand.peak_import_lower_bound_kw)))
			)
				throw new ApiError(502, "invalid_run_result");
			if (
				nonnegative(demand.additional_pv_use_upper_kwh) &&
				(!nonnegative(baseline.grid_export_kwh) ||
					!nonnegative(baseline.grid_import_kwh) ||
					demand.additional_pv_use_upper_kwh >
						Math.min(baseline.grid_export_kwh, baseline.grid_import_kwh))
			)
				throw new ApiError(502, "invalid_run_result");
			if (
				nonnegative(demand.peak_import_lower_bound_kw) &&
				(!nonnegative(baseline.peak_grid_import_kw) ||
					demand.peak_import_lower_bound_kw > baseline.peak_grid_import_kw)
			)
				throw new ApiError(502, "invalid_run_result");
		} else if (search.demand !== undefined) {
			const demand = readObject(c.demand);
			if (
				!["satisfied", "violated", "unresolved"].includes(
					String(demand.status),
				) ||
				typeof demand.reason !== "string" ||
				!demand.reason ||
				(demand.status === "satisfied" && demand.metrics === null)
			)
				throw new ApiError(502, "invalid_run_result");
			if (demand.metrics !== null) {
				const metrics = readObject(demand.metrics);
				const initial = readObject(metrics.stored_initial);
				for (const key of ["pv_kwh", "grid_kwh", "initial_unknown_kwh"]) {
					const value = initial[key];
					if (typeof value !== "number" || !Number.isFinite(value) || value < 0)
						throw new ApiError(502, "invalid_run_result");
				}
				for (const key of [
					"unserved_load_kwh",
					"maximum_interval_average_import_kw",
				]) {
					const value = metrics[key];
					if (typeof value !== "number" || !Number.isFinite(value) || value < 0)
						throw new ApiError(502, "invalid_run_result");
				}
			}
			if (demand.equipment !== null)
				readEquipmentAssessment(readObject(demand.equipment).assessment);
		} else if (c.demand !== undefined)
			throw new ApiError(502, "invalid_run_result");
		ids.add(String(c.id));
		if (
			coverage.template === "declared_plant_one_external_assembly_per_converter"
		) {
			if (
				c.selection !== undefined ||
				!matchesPlantSearch(
					readPlantSearch(coverage.plan),
					readEquipmentPlant(c.plant),
				)
			)
				throw new ApiError(502, "invalid_run_result");
		} else {
			if (c.plant !== undefined) throw new ApiError(502, "invalid_run_result");
			readEquipmentSelection(c.selection);
		}
		if (c.status === "satisfied") qualified++;
	}
	if (search.qualified_count !== qualified)
		throw new ApiError(502, "invalid_run_result");
	for (const value of search.products) {
		const p = readObject(value);
		if (
			!count(p.canonical_product_id) ||
			p.canonical_product_id === 0 ||
			typeof p.model !== "string" ||
			typeof p.brand !== "string" ||
			typeof p.sku !== "string" ||
			!hash(p.product_revision)
		)
			throw new ApiError(502, "invalid_run_result");
	}
	readObject(coverage.gaps);
	return result;
}
export function readEquipmentCandidate(
	value: unknown,
	runId: string,
	candidate: EquipmentCandidate,
): JsonObject {
	const reply = readObject(value);
	if (
		reply.run_id !== runId ||
		reply.candidate_id !== candidate.id ||
		reply.assessment_sha256 !== candidate.assessment_sha256
	)
		throw new ApiError(502, "invalid_run_result");
	const assessment = readEquipmentAssessment(reply.assessment);
	if (assessment.overall_status !== candidate.status)
		throw new ApiError(502, "invalid_run_result");
	return assessment;
}
