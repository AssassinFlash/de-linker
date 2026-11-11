import { ApiError, type JsonObject } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import { readCountryRuleInputs } from "../domain/countryRules.ts";
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

const ruleOutcomes: Record<string, readonly string[]> = {
	fr_generation_type: [
		"type_a",
		"type_b",
		"type_c",
		"type_d",
		"below_range",
		"missing_inputs",
		"outside_version",
	],
	nl_storage_type: [
		"type_a",
		"type_b",
		"type_c",
		"type_d",
		"below_range",
		"missing_inputs",
		"outside_version",
	],
	nl_storage_lfsm: [
		"statism_2_percent",
		"statism_1_percent",
		"boundary_not_established",
		"below_range",
		"missing_inputs",
		"outside_version",
	],
	de_eeg_control: [
		"fetch_and_reduce",
		"reduce",
		"no_requirement_in_9_2_1_2",
		"not_this_phase",
		"missing_inputs",
		"outside_version",
	],
	de_eeg_export: [
		"sixty_percent_conditionally",
		"not_in_tariff",
		"no_60_percent_in_9_2_2b_3",
		"exempt_plug_in",
		"not_this_phase",
		"missing_inputs",
		"outside_version",
	],
	fr_enedis_declaration: [
		"enedis_declare_cacsi",
		"missing_inputs",
		"outside_version",
	],
	fr_enedis_certification: [
		"enedis_consuel_or_attestation",
		"missing_inputs",
		"outside_version",
	],
	at_tor_scope: [
		"in_scope_below_250_kw_and_110_kv",
		"outside_scope",
		"missing_inputs",
		"outside_version",
	],
	at_kleinsterzeugungsanlage: [
		"kleinsterzeugungsanlage_two_weeks_notice",
		"not_kleinsterzeugungsanlage",
		"outside_scope",
		"missing_inputs",
		"outside_version",
	],
	at_network_disconnection_protection: [
		"external_network_disconnection_protection",
		"automatic_disconnection_device_r25",
		"outside_scope",
		"missing_inputs",
		"outside_version",
	],
	at_substantial_change: [
		"new_installation",
		"substantial_change_power_increase_above_15_percent",
		"power_criterion_not_exceeded_other_criteria_open",
		"outside_scope",
		"missing_inputs",
		"outside_version",
	],
	at_connection_route: [
		"notification_route_up_to_20_kw_net_active_power",
		"network_access_contract_required_above_20_kw",
		"missing_inputs",
		"outside_version",
	],
	at_conformity_evidence: [
		"declared_austrian_inverter_list",
		"declared_accredited_r25_report",
		"declared_vde_4105_with_r25_properties",
		"missing_inputs",
		"outside_version",
	],
};
const ruleIds: Record<string, readonly string[]> = {
	FR: ["fr_generation_type"],
	NL: ["nl_storage_type", "nl_storage_lfsm"],
	DE: ["de_eeg_control", "de_eeg_export"],
	AT: [
		"at_tor_scope",
		"at_kleinsterzeugungsanlage",
		"at_network_disconnection_protection",
		"at_substantial_change",
		"at_connection_route",
		"at_conformity_evidence",
	],
};
const ruleBasis: Record<string, string> = {
	FR: "fr_generation_pmax",
	NL: "nl_storage_max_active",
	DE: "de_pv_installed",
	AT: "at_tor_typ_a_max_capacity",
};
const ruleSource: Record<string, string> = {
	FR: "fr_arrete_article_35",
	NL: "nl_systeemcode_article_2_9",
	DE: "de_eeg_section_9",
	AT: "at_tor_erzeuger_typ_a_1_4",
};
/**
 * Sources an AT reading cites after the TOR part itself: the ElWG for the
 * connection route and the same TOR part for the conformity evidence. They are
 * fixed per country, so a review cannot smuggle in a different citation.
 */
const ruleExtraSources: Record<string, readonly string[]> = {
	AT: ["at_elwg_2025", "at_tor_erzeuger_typ_a_1_4_conformity"],
};
/** Which of the review's sources one AT check belongs to. */
const atCheckSource: Record<string, number> = {
	at_connection_route: 1,
	at_conformity_evidence: 2,
};
const unresolvedOutcomes = [
	"missing_inputs",
	"outside_version",
	"below_range",
	"boundary_not_established",
	"outside_scope",
	"power_criterion_not_exceeded_other_criteria_open",
];

function readRuleReview(value: unknown, country: string): JsonObject {
	const review = readObject(value);
	const fail = (): never => {
		throw new ApiError(502, "invalid_run_result");
	};
	const inputs = readCountryRuleInputs(review.inputs);
	if (!inputs) return fail();
	const enedisRoute =
		country === "FR" && inputs.fr_enedis_full_self_consumption === true;
	const expectedSources =
		1 + (ruleExtraSources[country]?.length ?? 0) + (enedisRoute ? 1 : 0);
	if (
		review.schema_version !== 1 ||
		review.country_code !== country ||
		inputs.basis !== ruleBasis[country] ||
		review.rule_date !== inputs.rule_date ||
		!Array.isArray(review.sources) ||
		review.sources.length !== expectedSources ||
		!Array.isArray(review.checks) ||
		review.checks.length !==
			(ruleIds[country]?.length ?? 0) + (enedisRoute ? 2 : 0)
	)
		fail();
	const sources = (review.sources as JsonObject[]).map((source) =>
		readObject(source),
	);
	const ids = sources.map((source) => String(source.id));
	const extra = ruleExtraSources[country] ?? [];
	if (
		ids[0] !== ruleSource[country] ||
		(enedisRoute &&
			ids[extra.length + 1] !== "fr_enedis_total_self_consumption") ||
		extra.some((id, index) => ids[index + 1] !== id)
	)
		fail();
	for (const source of sources)
		if (
			[
				"id",
				"title",
				"source_url",
				"clause",
				"evidence_snapshot_date",
				"text_sha256",
			].some((key) => typeof source[key] !== "string") ||
			!publicSourceUrl(String(source.source_url)) ||
			!/^[a-f0-9]{64}$/.test(String(source.text_sha256)) ||
			(source.edition !== null && typeof source.edition !== "string") ||
			(source.effective_from !== null &&
				typeof source.effective_from !== "string")
		)
			fail();
	const expectedChecks = [
		...(ruleIds[country] ?? []),
		...(enedisRoute
			? ["fr_enedis_declaration", "fr_enedis_certification"]
			: []),
	];
	const seen = new Set();
	for (const item of review.checks as JsonObject[]) {
		const check = readObject(item);
		const id = String(check.id),
			outcome = String(check.outcome);
		const missing = check.missing_inputs;
		if (!Array.isArray(missing)) return fail();
		if (
			!expectedChecks.includes(id) ||
			seen.has(id) ||
			!ruleOutcomes[id]?.includes(outcome) ||
			check.source_id !==
				(id.startsWith("fr_enedis_")
					? ids[ids.length - 1]
					: ids[atCheckSource[id] ?? 0]) ||
			check.status !==
				(unresolvedOutcomes.includes(outcome) ? "unresolved" : "conditional")
		)
			fail();
		const actual = readObject(check.actual);
		if (
			actual.power_kw !== inputs.power_kw ||
			actual.connection_voltage_kv !== inputs.connection_voltage_kv ||
			missing.some(
				(key) =>
					![
						"rule_date",
						"power_kw",
						"connection_voltage_kv",
						"de_before_control_test",
						"de_remuneration",
						"de_plug_in_exception",
						"apparent_power_kva",
						"net_active_power_kw",
						"at_existing_installation_change",
						"at_change_previous_power_kw",
						"at_conformity_basis",
					].includes(String(key)),
			)
		)
			fail();
		seen.add(id);
	}
	return review;
}

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
		!["not_assessed", "partially_assessed"].includes(
			String(country.numeric_rules),
		) ||
		country.standard_transition !== "not_assessed" ||
		(country.country_code !== null &&
			typeof country.country_code !== "string") ||
		![
			"dso_tab_evidence_requires_independent_verification",
			"country_rules_not_available",
			"country_rules_require_project_verification",
		].includes(String(country.reason))
	)
		fail();
	if (country.rule_review !== undefined) {
		if (typeof country.country_code !== "string") fail();
		try {
			readRuleReview(country.rule_review, country.country_code as string);
		} catch {
			fail();
		}
	} else if (
		country.numeric_rules !== "not_assessed" ||
		country.reason === "country_rules_require_project_verification"
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
