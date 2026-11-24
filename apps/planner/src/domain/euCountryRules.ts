import type { RuleBasis } from "./countryRules.ts";
import { __ } from "../i18n.ts";

export const euRuleFields = {
	it_lv_generation_spi: ["power_kw"],
	es_self_consumption: [
		"es_export_surplus",
		"power_kw",
		"es_serviced_urban_land",
	],
	gb_lv_microgeneration: [
		"gb_in_great_britain",
		"gb_permanently_wired",
		"current_per_phase_a",
		"gb_type_tested",
		"gb_multiple_premises",
	],
	pl_renewable_electric_installation: ["power_kw", "connection_voltage_kv"],
	be_small_plant_limits: [
		"be_three_phase",
		"be_generation_kva",
		"be_storage_kva",
	],
	ch_lv_generation_control: [
		"ch_new_installation",
		"power_kw",
		"apparent_power_kva",
	],
} as const;
export type EuBasis = keyof typeof euRuleFields;
export type EuField = (typeof euRuleFields)[EuBasis][number];
export function isEuBasis(basis: RuleBasis): basis is EuBasis {
	return Object.hasOwn(euRuleFields, basis);
}
export const euFieldUnits = {
	power_kw: "kW",
	connection_voltage_kv: "kV",
	apparent_power_kva: "kVA",
	gb_in_great_britain: "",
	gb_permanently_wired: "",
	current_per_phase_a: "A",
	gb_type_tested: "",
	gb_multiple_premises: "",
	es_export_surplus: "",
	es_serviced_urban_land: "",
	be_three_phase: "",
	be_generation_kva: "kVA",
	be_storage_kva: "kVA",
	ch_new_installation: "",
} as const;
export function euRuleScopes(): Record<string, string> {
	return {
		it_lv_generation_spi: __(
			"Compare the total generating power at the low-voltage grid connection with the CEI interface protection requirement.",
			"linker-tools",
		),
		es_self_consumption: __(
			"Check the permit route for generation supplying on-site consumption under Article 7 of RD 244/2019. For PV, use the installed power defined in Article 3(h).",
			"linker-tools",
		),
		gb_lv_microgeneration: __(
			"Check the low-voltage connection route under ENA G98 for England, Scotland and Wales. Use the aggregate registered current per phase at nominal 230 V.",
			"linker-tools",
		),
		pl_renewable_electric_installation: __(
			"Check the statutory power and voltage limits for a renewable electricity microinstallation.",
			"linker-tools",
		),
		be_small_plant_limits: __(
			"Check the standard AC power limits in Synergrid C10/11 for a small plant at a low-voltage connection. Count hybrid equipment under generation and separate storage under storage.",
			"linker-tools",
		),
		ch_lv_generation_control: __(
			"Check the control interface for new generating installations up to 250 kW on the Swiss low-voltage network (NE7).",
			"linker-tools",
		),
	};
}
export function euRuleLabels() {
	return {
		gb_plug_in_scope: __(
			"Plug-in equipment has separate G98 requirements. Confirm the specific unit and connection route with the DNO.",
			"linker-tools",
		),
		gb_permanently_wired: __(
			"Is all generation at the premises permanently wired?",
			"linker-tools",
		),

		it_lv_generation_spi: __(
			"Italy · LV generator interface protection",
			"linker-tools",
		),
		es_self_consumption: __(
			"Spain · self-consumption connection permits",
			"linker-tools",
		),
		gb_lv_microgeneration: __(
			"Great Britain · LV generation connection route",
			"linker-tools",
		),
		pl_renewable_electric_installation: __(
			"Poland · renewable electricity microinstallation",
			"linker-tools",
		),
		be_small_plant_limits: __(
			"Belgium · small generating plant power limits",
			"linker-tools",
		),
		ch_lv_generation_control: __(
			"Switzerland · LV generation control interface",
			"linker-tools",
		),
		it_interface_protection: __(
			"Interface protection at the LV connection",
			"linker-tools",
		),
		es_generation_access: __(
			"Access and connection permits for generation",
			"linker-tools",
		),
		gb_connection_route: __(
			"Application to the distribution network operator",
			"linker-tools",
		),
		pl_microinstallation_scope: __(
			"Statutory electrical microinstallation category",
			"linker-tools",
		),
		be_small_plant_power: __(
			"Power criterion for a small generating plant",
			"linker-tools",
		),
		ch_dso_interface: __(
			"Power control by the network operator",
			"linker-tools",
		),
		outside_lv_scope: __(
			"This reading covers connections to the low-voltage network. Ask the operator for the procedure at your connection voltage.",
			"linker-tools",
		),
		it_integrated_or_dedicated: __(
			"Up to 11.08 kW total generating power, CEI permits interface protection integrated in the converter or a dedicated protection relay. Confirm device conformity and the TICA connection procedure with your operator.",
			"linker-tools",
		),
		it_dedicated_relay: __(
			"Above 11.08 kW total generating power, a dedicated interface protection relay is required. Confirm the relay and the TICA connection procedure with your operator.",
			"linker-tools",
		),
		es_generation_permit_exempt: __(
			"The declared generation is exempt from access and connection permits under Article 7. Check permits for the consumption connection and other local requirements separately.",
			"linker-tools",
		),
		es_generation_permits: __(
			"This surplus generation requires access and connection permits. Check the consumption connection separately.",
			"linker-tools",
		),
		gb_single_g98_notice: __(
			"For this fully type-tested single-premises installation within the G98 current limit, notify the DNO within 28 days of commissioning. Confirm the installation and documentation requirements.",
			"linker-tools",
		),
		gb_cluster_agreement: __(
			"For installations at multiple premises in a close geographic region, obtain prior agreement from the DNO.",
			"linker-tools",
		),
		gb_g99_application: __(
			"The aggregate current exceeds the G98 limit. Apply to the DNO under G99 before connection.",
			"linker-tools",
		),
		gb_confirm_non_type_tested: __(
			"The G98 route requires fully type-tested equipment. Agree the applicable procedure and tests with the DNO before connection.",
			"linker-tools",
		),
		gb_other_territory: __(
			"This edition covers England, Scotland and Wales. Confirm the rules for the site with its network operator.",
			"linker-tools",
		),
		pl_microinstallation: __(
			"The renewable electricity installation meets the statutory microinstallation limits. Ask your operator to confirm the notification route and equipment evidence.",
			"linker-tools",
		),
		pl_outside_microinstallation: __(
			"This electrical installation is outside the microinstallation limits. Request the connection conditions from your network operator.",
			"linker-tools",
		),
		be_within_power_limits: __(
			"Both AC power totals are within the standard small-plant limits. Check separation protection, storage controls, special cases and regional DSO requirements before selecting the connection procedure.",
			"linker-tools",
		),
		be_above_power_limits: __(
			"At least one AC power total exceeds the three-phase small-plant limit. Ask the DSO for the applicable connection procedure.",
			"linker-tools",
		),
		be_check_local_single_phase_limit: __(
			"At least one AC power total exceeds 5 kVA. Check whether the regional DSO publishes a higher single-phase limit.",
			"linker-tools",
		),
		be_no_generating_units: __(
			"Enter the generating or storage equipment present at this connection.",
			"linker-tools",
		),
		ch_remote_disconnect: __(
			"For this new LV installation, provide the emergency interface for reducing feed-in to zero. Agree the implementation with the DSO.",
			"linker-tools",
		),
		ch_power_reduction: __(
			"In addition to emergency reduction to zero, provide a technical interface for the DSO to reduce active feed-in at any time.",
			"linker-tools",
		),
		ch_above_interface_scope: __(
			"Above 250 kW, confirm the interface under section 6.5.2 with the DSO.",
			"linker-tools",
		),
		ch_existing: __(
			"For an existing installation, ask your DSO whether the new-installation provisions apply to the planned change.",
			"linker-tools",
		),
		power_kw: __("Total installed generating power", "linker-tools"),
		connection_voltage_kv: __(
			"Nominal network voltage at the connection point",
			"linker-tools",
		),
		apparent_power_kva: __("Installed apparent power", "linker-tools"),
		gb_in_great_britain: __(
			"Is the site in England, Scotland or Wales?",
			"linker-tools",
		),
		current_per_phase_a: __(
			"Total registered generating current on the most heavily loaded phase",
			"linker-tools",
		),
		gb_type_tested: __(
			"Is all generating equipment fully type-tested to G98?",
			"linker-tools",
		),
		gb_multiple_premises: __(
			"Does this project cover multiple premises in a close geographic region?",
			"linker-tools",
		),
		es_export_surplus: __(
			"Will this self-consumption installation export surplus electricity?",
			"linker-tools",
		),
		es_serviced_urban_land: __(
			"Is the site on urbanised land with all legally required infrastructure and services?",
			"linker-tools",
		),
		be_three_phase: __("Is this a three-phase connection?", "linker-tools"),
		be_generation_kva: __(
			"Maximum AC power of generating units including hybrids (enter 0 if none)",
			"linker-tools",
		),
		be_storage_kva: __(
			"Maximum AC power of separate storage units (enter 0 if none)",
			"linker-tools",
		),
		ch_new_installation: __(
			"Is this a new generating installation?",
			"linker-tools",
		),
		voltage_level: __(
			"Network voltage level at the site connection",
			"linker-tools",
		),
	};
}
