import { validate2020 } from "../data/schemaValidator.ts";
import schema from "../contracts/country-rules.schema.json" with { type: "json" };
import { ApiError, type JsonObject } from "../data/protocol.ts";
import { isEuBasis } from "./euCountryRules.ts";
import { calendarDate, emptyGridConnection } from "./gridConnection.ts";

export type RuleBasis =
	| "fr_generation_pmax"
	| "nl_storage_max_active"
	| "de_pv_installed"
	| "at_tor_typ_a_max_capacity"
	| "se_rfg_maximum_capacity"
	| "it_lv_generation_spi"
	| "es_self_consumption"
	| "gb_lv_microgeneration"
	| "pl_renewable_electric_installation"
	| "be_small_plant_limits"
	| "ch_lv_generation_control";

export interface CountryRuleInputs extends JsonObject {
	schema_version: 1;
	basis: RuleBasis;
	rule_date: string | null;
	power_kw: number | null;
	connection_voltage_kv: number | null;
	de_before_control_test: boolean | null;
	de_remuneration: "feed_in_or_tenant" | "other" | null;
	de_plug_in_exception: boolean | null;
	fr_enedis_full_self_consumption: boolean | null;
	apparent_power_kva?: number | null;
	net_active_power_kw?: number | null;
	at_existing_installation_change?: boolean | null;
	at_change_previous_power_kw?: number | null;
	at_conformity_basis?:
		| "austrian_inverter_list"
		| "accredited_r25_report"
		| "vde_4105_with_r25_properties"
		| null;
	se_export_power_kw?: number | null;
	se_existing_installation_change?: boolean | null;
	gb_in_great_britain?: boolean | null;
	current_per_phase_a?: number | null;
	gb_permanently_wired?: boolean | null;
	gb_type_tested?: boolean | null;
	gb_multiple_premises?: boolean | null;
	es_export_surplus?: boolean | null;
	es_serviced_urban_land?: boolean | null;
	be_three_phase?: boolean | null;
	be_generation_kva?: number | null;
	be_storage_kva?: number | null;
	ch_new_installation?: boolean | null;
}

const validate = validate2020<CountryRuleInputs>(schema);

export function readCountryRuleInputs(
	value: unknown,
): CountryRuleInputs | undefined {
	if (value === undefined) return undefined;
	if (
		!validate(value) ||
		(value.rule_date !== null && !calendarDate(value.rule_date))
	)
		throw new ApiError(422, "invalid_country_rule_inputs");
	return value;
}

export function emptyCountryRuleInputs(basis: RuleBasis): CountryRuleInputs {
	return {
		schema_version: 1,
		basis,
		rule_date: null,
		power_kw: null,
		connection_voltage_kv: null,
		de_before_control_test: null,
		de_remuneration: null,
		de_plug_in_exception: null,
		fr_enedis_full_self_consumption: null,
		apparent_power_kva: null,
		net_active_power_kw: null,
		at_existing_installation_change: null,
		at_change_previous_power_kw: null,
		at_conformity_basis: null,
		se_export_power_kw: null,
		se_existing_installation_change: null,
	};
}

export function replaceCountryRuleInputs(
	inputs: JsonObject,
	value: CountryRuleInputs | undefined,
): JsonObject {
	const { country_rule_inputs: _removed, ...rest } = inputs;
	return value === undefined
		? rest
		: { ...rest, country_rule_inputs: readCountryRuleInputs(value)! };
}

export const ruleCountries: Record<RuleBasis, string> = {
	ch_lv_generation_control: "CH",
	be_small_plant_limits: "BE",
	pl_renewable_electric_installation: "PL",
	gb_lv_microgeneration: "GB",
	es_self_consumption: "ES",
	it_lv_generation_spi: "IT",
	fr_generation_pmax: "FR",
	nl_storage_max_active: "NL",
	de_pv_installed: "DE",
	at_tor_typ_a_max_capacity: "AT",
	se_rfg_maximum_capacity: "SE",
};
// Source-reading dates: docs/research/2026-10-23-modern-workbench/COUNTRY-EVIDENCE.md
// and docs/research/2026-11-12-se-country-rules/EVIDENCE.md.
export const CHECKED_SOURCE_DATES: Record<RuleBasis, string> = {
	ch_lv_generation_control: "2026-11-24",
	be_small_plant_limits: "2026-11-24",
	pl_renewable_electric_installation: "2026-11-24",
	gb_lv_microgeneration: "2026-11-24",
	es_self_consumption: "2026-11-24",
	it_lv_generation_spi: "2026-11-24",
	fr_generation_pmax: "2026-11-04",
	nl_storage_max_active: "2026-11-04",
	de_pv_installed: "2026-11-04",
	at_tor_typ_a_max_capacity: "2026-11-11",
	se_rfg_maximum_capacity: "2026-11-11",
};

export function newCountryRuleInputs(basis: RuleBasis): CountryRuleInputs {
	return {
		...emptyCountryRuleInputs(basis),
		rule_date: isEuBasis(basis) ? CHECKED_SOURCE_DATES[basis] : null,
	};
}

export function chooseCountryRules(
	inputs: JsonObject,
	country: string | null,
): JsonObject {
	const basis = (Object.keys(ruleCountries) as RuleBasis[]).find(
		(key) => ruleCountries[key] === country,
	);
	const { country_rule_inputs: _rules, ...rest } = inputs;
	return basis
		? {
				...rest,
				grid_connection: inputs.grid_connection ?? emptyGridConnection(),
				country_rule_inputs: newCountryRuleInputs(basis),
			}
		: rest;
}
