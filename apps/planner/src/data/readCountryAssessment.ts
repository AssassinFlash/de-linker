import { ApiError, type JsonObject } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import {
	publicSourceUrl,
	readGridConnection,
} from "../domain/gridConnection.ts";
export const gridCheckIds = [
	"responsible_dso",
	"connection_voltage",
	"applicable_tab",
	"independent_dso_tab_verification",
	"connection_permission",
] as const;
export function readCountryAssessment(value: unknown): JsonObject {
	const country = readObject(value);
	const fail = (): never => {
		throw new ApiError(502, "invalid_run_result");
	};
	if (country.status !== "unresolved") fail();
	// Earlier frozen reports retain the original country-assessment shape.
	if (country.model === undefined) return country;
	if (
		country.model !== "declared_grid_connection_evidence_v1" ||
		country.declaration_status !==
			"project_provided_not_independently_verified" ||
		country.independent_verification !== "not_assessed" ||
		country.connection_permission !== "not_established" ||
		country.numeric_rules !== "not_assessed" ||
		country.standard_transition !== "not_assessed" ||
		(country.country_code !== null &&
			typeof country.country_code !== "string") ||
		![
			"dso_tab_evidence_requires_independent_verification",
			"country_rules_not_available",
		].includes(String(country.reason))
	)
		fail();
	try {
		if (!readGridConnection(country.project_facts)) fail();
	} catch {
		fail();
	}
	if (
		!Array.isArray(country.checks) ||
		country.checks.length !== gridCheckIds.length ||
		!Array.isArray(country.missing_inputs) ||
		!Array.isArray(country.rule_sources)
	)
		return fail();
	const ids = new Set();
	for (const raw of country.checks) {
		const c = readObject(raw);
		if (
			!gridCheckIds.includes(c.id as (typeof gridCheckIds)[number]) ||
			ids.has(c.id) ||
			!["provided", "unresolved"].includes(String(c.status)) ||
			typeof c.reason !== "string" ||
			(["independent_dso_tab_verification", "connection_permission"].includes(
				String(c.id),
			) &&
				c.status !== "unresolved")
		)
			fail();
		ids.add(c.id);
	}
	const missing = [
		"country_code",
		"dso_name",
		"dso_source_url",
		"voltage_level",
		"tab.source_url",
		"tab.edition_or_date",
	];
	if (
		new Set(country.missing_inputs).size !== country.missing_inputs.length ||
		country.missing_inputs.some((v) => !missing.includes(String(v))) ||
		(country.country_code !== "DE" && country.rule_sources.length !== 0)
	)
		fail();
	const sourceIds = new Set();
	for (const raw of country.rule_sources) {
		const source = readObject(raw);
		if (
			[
				"id",
				"title",
				"clause",
				"evidence_snapshot_date",
				"evidence_basis",
				"scope",
			].some((key) => typeof source[key] !== "string") ||
			sourceIds.has(source.id) ||
			typeof source.source_url !== "string" ||
			!publicSourceUrl(source.source_url) ||
			(source.edition !== null && typeof source.edition !== "string") ||
			(source.raw_sha256 !== null &&
				(typeof source.raw_sha256 !== "string" ||
					!/^[a-f0-9]{64}$/.test(source.raw_sha256)))
		)
			fail();
		sourceIds.add(source.id);
	}
	return country;
}
