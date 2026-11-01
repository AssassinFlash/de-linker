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
		nl_storage_lfsm: __(
			"Dutch storage-unit low-frequency statism",
			"linker-tools",
		),
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
	};
	return (
		<section>
			<h5>{__("Dated national rule reading", "linker-tools")}</h5>
			<p>
				{__(
					"Results are conditional on the declared scope and values. The operator, applicable local requirements, equipment compliance and grid permission still need separate verification.",
					"linker-tools",
				)}
			</p>
			<p>
				{__(
					"This is a reference to the source on the selected date. Its applicability today and on the project connection date still needs verification.",
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
