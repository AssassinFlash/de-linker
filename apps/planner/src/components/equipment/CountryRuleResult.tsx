import type { JsonObject } from "../../data/protocol.ts";
import { __ } from "../../i18n.ts";
import { formatDecimal } from "../../domain/decimal.ts";

export function CountryRuleResult({
	review,
	locale,
}: {
	review: JsonObject;
	locale: string;
}) {
	const inputs = review.inputs as JsonObject;
	const labels: Record<string, string> = {
		fr_generation_type: __("French generation-unit category", "linker-tools"),
		nl_storage_type: __(
			"Dutch storage-unit corresponding requirements",
			"linker-tools",
		),
		nl_storage_lfsm: __("Dutch storage-unit LFSM-U droop", "linker-tools"),
		de_eeg_control: __("EEG pre-test remote control", "linker-tools"),
		de_eeg_export: __("EEG pre-test export limitation", "linker-tools"),
		fr_enedis_declaration: __(
			"Enedis declaration and agreement",
			"linker-tools",
		),
		fr_enedis_certification: __(
			"Enedis supporting documentation",
			"linker-tools",
		),
		at_tor_scope: __("Scope of TOR Erzeuger Typ A", "linker-tools"),
		at_kleinsterzeugungsanlage: __(
			"Kleinsterzeugungsanlage status",
			"linker-tools",
		),
		at_network_disconnection_protection: __(
			"Network disconnection protection",
			"linker-tools",
		),
		at_substantial_change: __(
			"Substantial change of an existing installation",
			"linker-tools",
		),
		at_connection_route: __("Connection route", "linker-tools"),
		at_conformity_evidence: __("Conformity evidence path", "linker-tools"),
	};
	const outcomes: Record<string, string> = {
		type_a: __("Type A", "linker-tools"),
		type_b: __("Type B", "linker-tools"),
		type_c: __("Type C", "linker-tools"),
		type_d: __("Type D", "linker-tools"),
		below_range: __(
			"Below the range covered by this rule reading",
			"linker-tools",
		),
		missing_inputs: __("More project information is needed", "linker-tools"),
		outside_version: __(
			"The chosen date is outside the documented version",
			"linker-tools",
		),
		statism_2_percent: __("2% in storage and generation modes", "linker-tools"),
		statism_1_percent: __("1% in storage and generation modes", "linker-tools"),
		boundary_not_established: __(
			"The 0.8 kW boundary is not established by this clause",
			"linker-tools",
		),
		fetch_and_reduce: __(
			"Actual export retrieval and remote reduction",
			"linker-tools",
		),
		reduce: __("Remote reduction", "linker-tools"),
		no_requirement_in_9_2_1_2: __(
			"No requirement under § 9(2) sentence 1 nos. 1–2 for this power",
			"linker-tools",
		),
		not_this_phase: __(
			"The declared project is beyond the pre-test phase; other requirements remain open",
			"linker-tools",
		),
		sixty_percent_conditionally: __(
			"60% of installed power at the grid connection point, under the stated conditions",
			"linker-tools",
		),
		not_in_tariff: __(
			"The declared remuneration is outside this 60% provision",
			"linker-tools",
		),
		no_60_percent_in_9_2_2b_3: __(
			"No 60% limit from § 9(2) sentence 1 nos. 2(b)–3 for this power",
			"linker-tools",
		),
		exempt_plug_in: __(
			"The declared plug-in solar exception applies to this provision",
			"linker-tools",
		),
		enedis_declare_cacsi: __(
			"Declare the installation through Enedis-Connect and accept the CACSI no-injection agreement",
			"linker-tools",
		),
		enedis_consuel_or_attestation: __(
			"Provide a Consuel certificate or declaration on honour. The source requires Consuel when modifying existing electrical circuits or adding a battery, with a possible plug-and-play exception subject to its stated conditions.",
			"linker-tools",
		),
		in_scope_below_250_kw_and_110_kv: __(
			"Inside this TOR part: maximum capacity below 250 kW and connection voltage below 110 kV",
			"linker-tools",
		),
		outside_scope: __(
			"Outside the scope of this TOR part; the cited provisions give no reading for this project",
			"linker-tools",
		),
		kleinsterzeugungsanlage_two_weeks_notice: __(
			"Kleinsterzeugungsanlage at up to 0.8 kW maximum capacity: written notice to the network operator at least two weeks before commissioning, and the residual requirements listed in § 2.1",
			"linker-tools",
		),
		not_kleinsterzeugungsanlage: __(
			"Not a Kleinsterzeugungsanlage: the exemption of § 2.1 does not apply",
			"linker-tools",
		),
		external_network_disconnection_protection: __(
			"External network disconnection protection required above 30 kVA",
			"linker-tools",
		),
		automatic_disconnection_device_r25: __(
			"Automatic disconnection device under OVE-Richtlinie R 25 permitted up to 30 kVA",
			"linker-tools",
		),
		new_installation: __(
			"New installation; the substantial-change provisions do not apply",
			"linker-tools",
		),
		substantial_change_power_increase_above_15_percent: __(
			"Maximum capacity increases by more than 15%: the cited example of a substantial change is met",
			"linker-tools",
		),
		power_criterion_not_exceeded_other_criteria_open: __(
			"The 15% example is not met; other substantial-change criteria stay open",
			"linker-tools",
		),
		notification_route_up_to_20_kw_net_active_power: __(
			"Up to 20 kW net active power: notification to the distribution system operator, connection on confirmation or after four weeks without a decision",
			"linker-tools",
		),
		network_access_contract_required_above_20_kw: __(
			"Above 20 kW net active power: a network access contract with the operator is required",
			"linker-tools",
		),
		declared_austrian_inverter_list: __(
			"Declared: entry in the Austrian inverter list. The listing, device and software version still need verification.",
			"linker-tools",
		),
		declared_accredited_r25_report: __(
			"Declared: accredited test report under OVE-Richtlinie R 25 including the Austrian settings. The report scope and device version still need verification.",
			"linker-tools",
		),
		declared_vde_4105_with_r25_properties: __(
			"Declared: VDE-AR-N 4105 report with the additional R 25 properties and Austrian parameters. The report scope and device version still need verification.",
			"linker-tools",
		),
	};
	const missing: Record<string, string> = {
		rule_date: __("rule date", "linker-tools"),
		power_kw: __("declared power", "linker-tools"),
		connection_voltage_kv: __("connection-point voltage", "linker-tools"),
		de_before_control_test: __("meter and control-test stage", "linker-tools"),
		de_remuneration: __("EEG remuneration", "linker-tools"),
		de_plug_in_exception: __(
			"complete plug-in solar exception",
			"linker-tools",
		),
		apparent_power_kva: __(
			"apparent power at the connection point",
			"linker-tools",
		),
		net_active_power_kw: __("agreed net active power", "linker-tools"),
		at_existing_installation_change: __(
			"existing installation being changed",
			"linker-tools",
		),
		at_change_previous_power_kw: __(
			"maximum capacity before the change",
			"linker-tools",
		),
		at_conformity_basis: __("declared conformity path", "linker-tools"),
	};
	return (
		<section>
			<h5>{__("Dated national rule reading", "linker-tools")}</h5>
			<p>
				{__(
					"This is a conditional reference for the selected rule date and declared project scope and values. Verify whether the cited rules apply today and on the project's grid connection date. The grid operator, connection voltage, local requirements, equipment compliance and grid permission need separate verification.",
					"linker-tools",
				)}
			</p>
			<dl className="lp-profile-facts">
				<div>
					<dt>
						{__("Date for this rule reading (YYYY-MM-DD)", "linker-tools")}
					</dt>
					<dd>{String(review.rule_date ?? "—")}</dd>
				</div>
				<div>
					<dt>{__("Declared power", "linker-tools")}</dt>
					<dd>
						{typeof inputs.power_kw !== "number"
							? "—"
							: `${formatDecimal(inputs.power_kw, locale)} kW`}
					</dd>
				</div>
				{review.country_code === "FR" && (
					<div>
						<dt>
							{__("Voltage at the grid connection point", "linker-tools")}
						</dt>
						<dd>
							{typeof inputs.connection_voltage_kv !== "number"
								? "—"
								: `${formatDecimal(inputs.connection_voltage_kv, locale)} kV`}
						</dd>
					</div>
				)}
			</dl>
			<ul>
				{(review.checks as JsonObject[]).map((check) => (
					<li key={String(check.id)}>
						<strong>{labels[String(check.id)]}</strong>:{" "}
						{outcomes[String(check.outcome)]}
						{(check.missing_inputs as string[]).length > 0 && (
							<>
								{" "}
								· {__("Information still missing", "linker-tools")}:{" "}
								{(check.missing_inputs as string[])
									.map((key) => missing[key])
									.join(", ")}
							</>
						)}
					</li>
				))}
			</ul>
			{(review.sources as JsonObject[]).map((source) => (
				<p key={String(source.id)}>
					<a
						href={String(source.source_url)}
						target="_blank"
						rel="noopener noreferrer"
					>
						{String(source.title)} · {String(source.clause)}
					</a>
					{source.edition && <> · {String(source.edition)}</>} ·{" "}
					{__("Evidence snapshot date", "linker-tools")}:{" "}
					{String(source.evidence_snapshot_date)}
				</p>
			))}
		</section>
	);
}
