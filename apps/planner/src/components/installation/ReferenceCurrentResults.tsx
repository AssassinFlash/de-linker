import type { CableQuantity } from "../../domain/installation.ts";
import type { ElectricalReview } from "../../domain/installationElectrical.ts";
import { CableSource, RevisionCode } from "./CableReferenceFacts.tsx";
import { electricalText } from "./ElectricalConditionFields.tsx";
import { layingLabel } from "./ReferenceCurrentFields.tsx";

export function ReferenceCurrentResults({
	review,
	cables,
	locale,
}: {
	review: ElectricalReview;
	cables: readonly CableQuantity[];
	locale: string;
}) {
	const segments = review.reference_current_segments ?? [];
	if (!segments.length) return null;
	const t = (en: string, de: string) => electricalText(locale, en, de),
		n = (value: number) =>
			new Intl.NumberFormat(locale, {
				maximumSignificantDigits: 6,
				useGrouping: false,
			}).format(value),
		status = {
			not_evaluated: t("Comparison unavailable", "Vergleich nicht möglich"),
			below_reference: t("Below the listed current", "Unter dem Tabellenwert"),
			equal_reference: t(
				"Equal to the listed current",
				"Entspricht dem Tabellenwert",
			),
			above_reference: t("Above the listed current", "Über dem Tabellenwert"),
		},
		reasons = {
			operating_condition_missing: t(
				"No operating condition recorded.",
				"Betriebsfall fehlt.",
			),
			circuit_kind_not_supported: t(
				"A PV DC circuit is required.",
				"Ein PV-Gleichstromkreis ist erforderlich.",
			),
			condition_method_not_supported: t(
				"A DC operating condition is required.",
				"Ein Gleichstrom-Betriebsfall ist erforderlich.",
			),
			current_path_not_single_pair: t(
				"One separate conductor for each polarity is required.",
				"Je Polarität ist ein einzelner Leiter erforderlich.",
			),
			current_path_not_confirmed: t(
				"The unbranched current path is not confirmed for both conductors.",
				"Der unverzweigte Strompfad ist nicht für beide Leiter bestätigt.",
			),
			installation_conditions_not_confirmed: t(
				"The installation conditions are not confirmed.",
				"Die Verlegebedingungen sind nicht bestätigt.",
			),
			confirmation_context_changed: t(
				"The saved confirmation does not match the current physical conditions. Review and confirm them again.",
				"Die gespeicherte Bestätigung passt nicht zu den aktuellen physikalischen Bedingungen. Prüfen und bestätigen Sie diese erneut.",
			),
			touching_pair_mismatch: t(
				"The touching conductors are not recorded as a matching pair.",
				"Die berührenden Leiter sind nicht als passendes Paar erfasst.",
			),
			cable_reference_unavailable: t(
				"The exact cable reference is unavailable.",
				"Die genaue Kabelreferenz ist nicht verfügbar.",
			),
			cable_specification_mismatch: t(
				"The declared conductor differs from the cable reference.",
				"Der erklärte Leiter weicht von der Kabelreferenz ab.",
			),
			reference_rating_unavailable: t(
				"The selected manufacturer table row is unavailable.",
				"Die gewählte Herstellertabellenzeile ist nicht verfügbar.",
			),
			reference_rating_conditions_mismatch: t(
				"The declaration differs from the table conditions.",
				"Die Erklärung weicht von den Tabellenbedingungen ab.",
			),
			reference_source_unavailable: t(
				"The cited document could not be verified.",
				"Das angegebene Dokument konnte nicht geprüft werden.",
			),
		};
	return (
		<section className="lp-scenario-block">
			<h3>
				{t(
					"Conductor current compared with the manufacturer's table",
					"Leiterstrom im Vergleich zur Herstellertabelle",
				)}
			</h3>
			<p>
				{t(
					"This compares each declared conductor with one manufacturer table row. The conductor temperature in that row is a table condition, not a measured site temperature. Cable sizing, protection and the complete installation still require separate checks.",
					"Dieser Vergleich bezieht jeden erklärten Leiter auf eine Herstellertabellenzeile. Die dortige Leitertemperatur ist eine Tabellenbedingung und kein vor Ort gemessener Wert. Kabelauslegung, Schutz und die gesamte Installation erfordern weitere Prüfungen.",
				)}
			</p>
			{segments.map((segment, index) => {
				const circuit = review.circuits.find(
						(row) => row.circuit_id === segment.circuit_id,
					),
					condition = circuit?.conditions.find(
						(row) => row.condition_id === segment.condition_id,
					),
					cable = cables.find((row) => row.id === segment.run_id);
				return (
					<article
						key={
							segment.circuit_id +
							":" +
							(segment.condition_id ?? "none") +
							":" +
							segment.run_id +
							":" +
							index
						}
					>
						<h4>
							{[
								circuit?.name ?? segment.circuit_id,
								condition?.name,
								cable?.name ?? segment.run_id,
							]
								.filter(Boolean)
								.join(" · ")}
						</h4>
						<p>{status[segment.status]}</p>
						{segment.reasons.length > 0 && (
							<ul>
								{segment.reasons.map((reason) => (
									<li key={reason}>{reasons[reason]}</li>
								))}
							</ul>
						)}
						{segment.project_current_a !== null &&
							segment.reference_current_a !== null && (
								<p>
									{t(
										"Operating current / listed current",
										"Strom im Betriebsfall / Tabellenwert",
									)}
									: {n(segment.project_current_a)} A /{" "}
									{n(segment.reference_current_a)} A
								</p>
							)}
						<p>
							{t(
								"Basis for project conditions",
								"Grundlage der Projektbedingungen",
							)}
							: {segment.installation.source_note}
						</p>
						{segment.rating && (
							<>
								<p>
									{layingLabel(segment.rating.laying, locale)} ·{" "}
									{n(segment.rating.current_a)} A · {t("Ambient", "Umgebung")}{" "}
									{n(segment.rating.ambient_temperature_c)} °C ·{" "}
									{t(
										"Conductor (table condition)",
										"Leiter (Tabellenbedingung)",
									)}{" "}
									{n(segment.rating.rated_conductor_temperature_c)} °C
								</p>
								{segment.product_revision && (
									<p>
										{t("Product revision", "Produktrevision")}:{" "}
										<RevisionCode value={segment.product_revision} />
									</p>
								)}
								<CableSource source={segment.rating.source} locale={locale} />
							</>
						)}
					</article>
				);
			})}
		</section>
	);
}
