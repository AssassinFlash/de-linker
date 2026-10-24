import type { JsonObject } from "./protocol.ts";
import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import { sameJson } from "../domain/draft.ts";

export const EQUIPMENT_TASK = "qualify_woo_equipment_v1";
const status = (s: unknown) =>
	["satisfied", "violated", "unresolved"].includes(String(s));
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
	const ids = new Set<string>();
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
		ids.add(check.id);
		for (const value of check.facts) {
			const fact = readObject(value);
			if (fact.source !== null) {
				const source = readObject(fact.source);
				if (
					typeof source.url !== "string" ||
					typeof source.page !== "number" ||
					!Number.isSafeInteger(source.page) ||
					source.page < 1
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
		}
	}
	const checks = assessment.checks.map(readObject),
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
			typeof line.model !== "string" ||
			typeof line.brand !== "string" ||
			typeof line.sku !== "string" ||
			(line.quantity !== null &&
				(typeof line.quantity !== "number" ||
					!Number.isSafeInteger(line.quantity) ||
					line.quantity <= 0))
		)
			throw new ApiError(502, "invalid_run_result");
	}
	return result;
}
