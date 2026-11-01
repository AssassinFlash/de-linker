import Ajv2020 from "ajv/dist/2020.js";
import schema from "../contracts/country-rules.schema.json" with { type: "json" };
import { ApiError, type JsonObject } from "../data/protocol.ts";
import { calendarDate } from "./gridConnection.ts";

export type RuleBasis =
	"fr_generation_pmax" | "nl_storage_max_active" | "de_pv_installed";

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
}

const validate = new Ajv2020({
	strict: true,
	strictNumbers: true,
}).compile<CountryRuleInputs>(schema);

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
