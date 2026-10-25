import type { JsonObject } from "./protocol.ts";
import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import { sameJson } from "../domain/draft.ts";

export const EQUIPMENT_TASK = "qualify_woo_equipment_v1";
const status = (s: unknown) =>
	["satisfied", "violated", "unresolved"].includes(String(s));
export function documentReference(value: unknown, requirePage = false) {
	const source = readObject(value);
	if (
		typeof source.url !== "string" ||
		((requirePage || source.page != null) &&
			(typeof source.page !== "number" ||
				!Number.isSafeInteger(source.page) ||
				source.page < 1))
	)
		throw new ApiError(502, "invalid_run_result");
	const url = new URL(source.url);
	if (
		url.protocol !== "https:" ||
		!["de-linker.com", "www.de-linker.com"].includes(url.hostname) ||
		url.username ||
		url.password
	)
		throw new ApiError(502, "invalid_run_result");
}
export function readEquipmentResult(
	value: unknown,
	run: JsonObject,
	manifest: JsonObject,
): JsonObject {
	const result = readObject(value),
		context = readObject(manifest.context),
		pinned = readObject(result.pinned_assets),
		assessment = readObject(result.assessment);
	if (
		result.schema !== 1 ||
		result.kind !== EQUIPMENT_TASK ||
		result.project_id !== run.project_id ||
		result.revision !== run.revision ||
		result.input_sha256 !== manifest.input_sha256 ||
		result.manifest_sha256 !== run.manifest_sha256 ||
		result.runtime_sha256 !== context.code_sha256 ||
		!sameJson(pinned, context.assets) ||
		typeof pinned["woo.equipment_inputs"] !== "string" ||
		!/^[a-f0-9]{64}$/.test(pinned["woo.equipment_inputs"]) ||
		!status(assessment.equipment_status) ||
		!["unresolved", "violated"].includes(String(assessment.overall_status)) ||
		!Array.isArray(assessment.checks) ||
		!Array.isArray(assessment.provisional_bill_of_materials) ||
		!Array.isArray(assessment.selected_products)
	)
		throw new ApiError(502, "invalid_run_result");
	readEquipmentAssessment(assessment);
	return result;
}

export function readEquipmentAssessment(value: unknown): JsonObject {
	const assessment = readObject(value);
	if (
		!status(assessment.equipment_status) ||
		!["unresolved", "violated"].includes(String(assessment.overall_status)) ||
		!Array.isArray(assessment.checks) ||
		!Array.isArray(assessment.provisional_bill_of_materials) ||
		!Array.isArray(assessment.selected_products)
	)
		throw new ApiError(502, "invalid_run_result");
	if (assessment.installation_requirements !== undefined) {
		if (!Array.isArray(assessment.installation_requirements))
			throw new ApiError(502, "invalid_run_result");
		for (const value of assessment.installation_requirements) {
			const r = readObject(value);
			if (
				!Array.isArray(r.conditions) ||
				!Array.isArray(r.documents) ||
				typeof r.included !== "boolean"
			)
				throw new ApiError(502, "invalid_run_result");
			for (const doc of r.documents) documentReference(doc);
		}
	}
	for (const value of assessment.selected_products) {
		const product = readObject(value);
		if (
			typeof product.product_id !== "number" ||
			!Number.isSafeInteger(product.product_id) ||
			product.product_id <= 0 ||
			["model", "brand", "sku"].some(
				(key) => key in product && typeof product[key] !== "string",
			)
		)
			throw new ApiError(502, "invalid_run_result");
	}
	const ids = new Set<string>();
	if (assessment.pv_electrical !== undefined) {
		const pv = readObject(assessment.pv_electrical);
		if (
			pv.schema_version !== 1 ||
			pv.method !== "woo_layout_linear_voc_stc_v1" ||
			!Array.isArray(pv.strings)
		)
			throw new ApiError(502, "invalid_run_result");
		for (const item of pv.strings) {
			const row = readObject(item);
			if (
				typeof row.id !== "string" ||
				!Array.isArray(row.module_ids) ||
				row.module_ids.length !== row.module_count ||
				!row.module_ids.every((id) => typeof id === "string") ||
				![row.mppt, row.input, row.module_count].every(
					(v) => typeof v === "number" && Number.isSafeInteger(v) && v > 0,
				) ||
				![row.stc_vmpp_v, row.cold_voc_v].every(
					(v) =>
						v === null ||
						(typeof v === "number" && Number.isFinite(v) && v > 0),
				)
			)
				throw new ApiError(502, "invalid_run_result");
		}
	}
	for (const value of assessment.checks) {
		const check = readObject(value);
		if (
			typeof check.id !== "string" ||
			ids.has(check.id) ||
			!status(check.status) ||
			typeof check.reason !== "string" ||
			!Array.isArray(check.facts)
		)
			throw new ApiError(502, "invalid_run_result");
		if (check.derivation !== undefined) {
			const d = readObject(check.derivation);
			if (
				d.operation !== "multiply" ||
				d.unit !== "kWh" ||
				!Array.isArray(d.factors) ||
				d.factors.length !== 2 ||
				!d.factors.every(
					(v) => typeof v === "number" && Number.isFinite(v) && v >= 0,
				) ||
				typeof check.actual !== "number"
			)
				throw new ApiError(502, "invalid_run_result");
		}
		ids.add(check.id);
		for (const value of check.facts) {
			const fact = readObject(value);
			if (fact.source !== null) {
				documentReference(fact.source, true);
			}
		}
	}
	const checks = assessment.checks.map((value) => readObject(value)),
		expected = checks.some((c) => c.status === "violated")
			? "violated"
			: checks.some((c) => c.status === "unresolved")
				? "unresolved"
				: "satisfied";
	if (
		assessment.equipment_status !== expected ||
		readObject(assessment.country_assessment).status !== "unresolved" ||
		assessment.overall_status !==
			(expected === "violated" ? "violated" : "unresolved")
	)
		throw new ApiError(502, "invalid_run_result");
	for (const value of assessment.provisional_bill_of_materials) {
		const line = readObject(value);
		if (
			typeof line.product_id !== "number" ||
			!Number.isSafeInteger(line.product_id) ||
			line.product_id <= 0 ||
			["model", "brand", "sku"].some(
				(key) => key in line && typeof line[key] !== "string",
			) ||
			(line.quantity !== null &&
				(typeof line.quantity !== "number" ||
					!Number.isSafeInteger(line.quantity) ||
					line.quantity <= 0))
		)
			throw new ApiError(502, "invalid_run_result");
	}
	return assessment;
}
