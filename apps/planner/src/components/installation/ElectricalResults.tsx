import type { ElectricalReview } from "../../domain/installationElectrical.ts";
import { electricalText } from "./ElectricalConditionFields.tsx";
import { CableSource, RevisionCode } from "./CableReferenceFacts.tsx";
export function ElectricalResults({
	review,
	locale,
}: {
	review: ElectricalReview;
	locale: string;
}) {
	const t = (en: string, de: string) => electricalText(locale, en, de);
	// Match installation_electrical_report.py::_number (.6g): six significant
	// digits for presentation only; frozen values and editable inputs stay exact.
	const numbers = new Intl.NumberFormat(locale, {
		maximumSignificantDigits: 6,
		useGrouping: false,
	});
	const n = (v: number | null) => (v === null ? "—" : numbers.format(v));
	const reasons: Record<string, string> = {
		dc_condition_not_applicable: t(
			"DC conditions do not apply to this circuit.",
			"DC-Bedingungen sind für diesen Stromkreis nicht anwendbar.",
		),
		ac_condition_not_applicable: t(
			"AC method requires explicit sinusoidal current, frequency, power factor and arrangement; three-phase requires balance.",
			"Das AC-Verfahren benötigt ausdrückliche Angaben zu Sinusform, Frequenz, Leistungsfaktor und Anordnung; dreiphasig zusätzlich Symmetrie.",
		),
		cable_runs_missing: t(
			"No physical cable runs recorded.",
			"Keine physischen Kabelstrecken erfasst.",
		),
		core_roles_missing: t(
			"Physical core roles missing.",
			"Funktionen physischer Adern fehlen.",
		),
		core_roles_not_applicable: t(
			"Core roles do not match this method.",
			"Aderfunktionen passen nicht zum Verfahren.",
		),
		cable_reference_unavailable: t(
			"Cable manufacturer reference or its exact revision unavailable.",
			"Kabelherstellerreferenz oder deren genaue Revision nicht verfügbar.",
		),
		cable_specification_mismatch: t(
			"Declared section, construction or core count differs from manufacturer facts.",
			"Erklärter Querschnitt, Aufbau oder Aderzahl weicht von Herstellerdaten ab.",
		),
		cable_conditions_mismatch: t(
			"No manufacturer parameter set matches the operating conditions.",
			"Kein Herstellerparametersatz passt zu den Betriebsbedingungen.",
		),
		cable_parameter_set_ambiguous: t(
			"More than one parameter set matches.",
			"Mehrere Parametersätze passen.",
		),
		route_quantity_unconfirmed: t(
			"Route length remains unconfirmed.",
			"Streckenlänge ist noch unbestätigt.",
		),
		numerical_range_not_supported: t(
			"Values exceed the supported numerical range.",
			"Werte überschreiten den unterstützten Zahlenbereich.",
		),
		parallel_or_branched_cores_not_supported: t(
			"Parallel or branched cores are outside this method.",
			"Parallele oder verzweigte Adern liegen außerhalb dieses Verfahrens.",
		),
		current_path_incomplete: t(
			"Current path incomplete.",
			"Strompfad unvollständig.",
		),
		phase_impedances_not_equal: t(
			"Phase impedances differ; balanced calculation cannot apply.",
			"Phasenimpedanzen unterscheiden sich; symmetrische Berechnung ist nicht anwendbar.",
		),
	};
	return (
		<section className="lp-scenario-block">
			<h3>
				{t(
					"Circuit voltage drop and conductor loss",
					"Spannungsfall und Leiterverluste",
				)}
			</h3>
			<p>
				{t(
					"Results cover only declared conductor segments. Connections, terminals, thermal loading, protection, earthing and country approval remain separate checks. Calculated values and a project-limit comparison do not qualify an installation.",
					"Die Ergebnisse gelten nur für erklärte Leiterabschnitte. Verbindungen, Klemmen, thermische Belastung, Schutz, Erdung und nationale Freigabe bleiben gesonderte Prüfungen. Berechnungswerte und Projektgrenzwertvergleich erteilen keine Installationsfreigabe.",
				)}
			</p>
			{review.circuits.map((c) => (
				<section key={c.circuit_id}>
					<h4>{c.name}</h4>
					{c.status === "not_recorded" && (
						<p>
							{t(
								"No operating conditions recorded.",
								"Keine Betriebsbedingungen erfasst.",
							)}
						</p>
					)}
					{c.conditions.map((r) => (
						<article key={r.condition_id}>
							<h5>
								{r.name} ·{" "}
								{r.status === "calculated"
									? t(
											"Calculated · not qualified",
											"Berechnet · nicht freigegeben",
										)
									: r.status === "data_insufficient"
										? t("Data insufficient", "Daten unzureichend")
										: t("Method not applicable", "Verfahren nicht anwendbar")}
							</h5>
							<p>
								{r.condition.method === "dc_resistive"
									? t("DC resistive loop", "DC-Widerstandsschleife")
									: r.condition.method === "ac_two_wire"
										? t("AC two-wire", "AC-Zweileiter")
										: t(
												"AC balanced three-phase",
												"AC symmetrisch dreiphasig",
											)}{" "}
								· {n(r.condition.current_a)} A ·{" "}
								{n(r.condition.reference_voltage_v)} V ·{" "}
								{n(r.condition.conductor_temperature_c)} °C ·{" "}
								{r.condition.direction === "start_to_end"
									? t("From → To", "Von → Nach")
									: t("To → From", "Nach → Von")}
							</p>
							<p>
								{t(
									"Operating-condition source",
									"Quelle der Betriebsbedingungen",
								)}
								: {r.condition.source_note}
							</p>
							{r.condition.method !== "dc_resistive" && (
								<p>
									{t("AC conditions", "AC-Bedingungen")}:{" "}
									{n(r.condition.frequency_hz)} Hz · cos φ{" "}
									{n(r.condition.power_factor)} ·{" "}
									{r.condition.reactive_direction === "lagging"
										? t("lagging", "nacheilend")
										: r.condition.reactive_direction === "leading"
											? t("leading", "voreilend")
											: "—"}{" "}
									· {r.condition.arrangement ?? "—"} ·{" "}
									{t("Sinusoidal", "Sinusförmig")}:{" "}
									{r.condition.sinusoidal ? t("yes", "ja") : t("no", "nein")} ·{" "}
									{t("Balanced", "Symmetrisch")}:{" "}
									{r.condition.balanced === null
										? "—"
										: r.condition.balanced
											? t("yes", "ja")
											: t("no", "nein")}
								</p>
							)}
							{r.reasons.length > 0 && (
								<ul>
									{r.reasons.map((code) => (
										<li key={code}>{reasons[code]}</li>
									))}
								</ul>
							)}
							<p>
								{r.value_basis === "resistance_upper_bound"
									? r.status === "calculated"
										? t(
												"Maximum resistance basis: upper bound for the signed conductor voltage drop under the declared conditions.",
												"Maximaler Widerstand: Obergrenze des vorzeichenbehafteten Leiterspannungsfalls unter den erklärten Bedingungen.",
											)
										: t(
												"Maximum resistance parameters are available for some conductor segments. No complete circuit result is available.",
												"Für einzelne Leiterabschnitte liegen maximale Widerstandsparameter vor. Ein vollständiges Stromkreisergebnis liegt nicht vor.",
											)
									: r.value_basis === "nominal_parameters"
										? t(
												"Nominal manufacturer parameters; not a measured actual value.",
												"Hersteller-Nennparameter; kein gemessener Istwert.",
											)
										: r.value_basis === "mixed_resistance_parameters"
											? t(
													"Mixed maximum and nominal resistance; not an overall upper bound.",
													"Gemischte maximale und nominelle Widerstände; keine Gesamtobergrenze.",
												)
											: t(
													"No resistance basis available.",
													"Keine Widerstandsgrundlage verfügbar.",
												)}
							</p>
							{r.status === "calculated" && (
								<dl>
									<dt>
										{t("Conductor voltage drop", "Spannungsfall der Leiter")}
									</dt>
									<dd>
										{n(r.voltage_drop_v)} V · {n(r.voltage_drop_percent)} %
									</dd>
									<dt>
										{t(
											"End voltage minus start voltage",
											"Endspannung minus Anfangsspannung",
										)}
									</dt>
									<dd>{n(r.end_minus_start_voltage_v)} V</dd>
									<dt>{t("Conductor loss", "Leiterverlust")}</dt>
									<dd>{n(r.conductor_loss_w)} W</dd>
									<dt>
										{t(
											"Sum of conductor resistance / reactance",
											"Summe der Leiterwiderstände / Reaktanzen",
										)}
									</dt>
									<dd>
										{n(r.loop_resistance_ohm)} Ω / {n(r.loop_reactance_ohm)} Ω
									</dd>
								</dl>
							)}
							<p>
								{r.limit.status === "not_declared"
									? t(
											"No project limit declared.",
											"Kein Projektgrenzwert erklärt.",
										)
									: r.limit.status === "not_evaluated"
										? t(
												"Project limit not evaluated.",
												"Projektgrenzwert nicht bewertet.",
											)
										: r.limit.status === "within_declared_limit"
											? t(
													"Within the declared project limit; no installation approval.",
													"Innerhalb des erklärten Projektgrenzwerts; keine Installationsfreigabe.",
												)
											: t(
													"Exceeds the declared project limit.",
													"Erklärter Projektgrenzwert überschritten.",
												)}
								{r.limit.declared &&
									` ${n(r.limit.declared.maximum_percent)} % · ${r.limit.declared.source_note}`}
							</p>
							{r.limit.reason && (
								<p>
									{t(
										"Maximum resistance does not bound the absolute voltage rise for this leading AC condition; the project limit cannot be assessed.",
										"Der maximale Widerstand begrenzt den Betrag der Spannungserhöhung bei diesem voreilenden AC-Strom nicht; der Projektgrenzwert ist nicht bewertbar.",
									)}
								</p>
							)}
							{r.segments.map((s) => (
								<details key={s.run_id + s.role}>
									<summary>
										{s.run_id} ·{" "}
										{
											{
												dc_positive: "DC +",
												dc_negative: "DC −",
												line: t("Line", "Außenleiter"),
												neutral: t("Neutral", "Neutralleiter"),
												l1: "L1",
												l2: "L2",
												l3: "L3",
												pe: "PE",
												unused: t("Unused", "Unbenutzt"),
											}[s.role]
										}{" "}
										· {n(s.length_m)} m · R {n(s.resistance_ohm)} Ω
										{s.reactance_ohm !== null
											? ` · X ${n(s.reactance_ohm)} Ω`
											: ""}
									</summary>
									<p>
										{t("Cable product", "Kabelprodukt")} {s.product_id} ·{" "}
										{s.parameter_set_id} ·{" "}
										{s.resistance_basis === "maximum"
											? t("Maximum resistance", "Maximaler Widerstand")
											: t("Nominal resistance", "Nennwiderstand")}
									</p>
									<p>
										{t("Product revision", "Produktrevision")}:{" "}
										<RevisionCode value={s.product_revision} />
									</p>
									<CableSource source={s.source} locale={locale} />
								</details>
							))}
						</article>
					))}
				</section>
			))}
		</section>
	);
}
