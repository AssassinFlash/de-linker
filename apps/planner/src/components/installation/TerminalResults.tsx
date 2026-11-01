import type { InstallationInputs } from "../../domain/installation.ts";
import type {
	TerminalAssessment,
	TerminalStatus,
	DomainStatus,
	UseStatus,
} from "../../domain/installationTerminals.ts";
import { electricalText } from "./ElectricalConditionFields.tsx";
import { CableSource, RevisionCode } from "./CableReferenceFacts.tsx";
import {
	communicationUseLabel,
	terminalDomainLabel,
} from "./installationLabels.ts";

export function TerminalResults({
	review,
	plan,
	locale,
}: {
	review: TerminalAssessment;
	plan: InstallationInputs;
	locale: string;
}) {
	const t = (en: string, de: string) => electricalText(locale, en, de);
	const status: Record<TerminalStatus, string> = {
		not_bound: t("No terminal selected", "Kein Anschluss ausgewählt"),
		instance_mismatch: t(
			"Saved selection belongs to different device data",
			"Gespeicherte Auswahl gehört zu anderen Gerätedaten",
		),
		product_unavailable: t(
			"Product data unavailable",
			"Produktdaten nicht verfügbar",
		),
		product_revision_changed: t(
			"Product revision changed",
			"Produktrevision hat sich geändert",
		),
		fact_unavailable: t(
			"Manufacturer fact unavailable",
			"Herstellerangabe nicht verfügbar",
		),
		document_changed: t(
			"Manufacturer document changed",
			"Herstellerdokument hat sich geändert",
		),
		terminal_unavailable: t(
			"Terminal no longer listed",
			"Anschluss nicht mehr aufgeführt",
		),
		invalid_evidence: t(
			"Manufacturer evidence unavailable or invalid",
			"Herstellernachweis nicht verfügbar oder ungültig",
		),
		documented: t(
			"Manufacturer terminal documented",
			"Herstelleranschluss dokumentiert",
		),
	};
	const domain: Record<DomainStatus, string> = {
		not_assessed: t("Not assessed", "Nicht geprüft"),
		matches: t("Matches circuit type", "Passt zum Stromkreistyp"),
		mismatch: t("Does not match circuit type", "Passt nicht zum Stromkreistyp"),
	};
	const use: Record<UseStatus, string> = {
		not_assessed: t("Not assessed", "Nicht geprüft"),
		not_declared: t(
			"Circuit use not declared",
			"Verwendungszweck des Stromkreises nicht angegeben",
		),
		not_documented: t(
			"Terminal use not documented",
			"Verwendungszweck des Anschlusses nicht dokumentiert",
		),
		matches: t(
			"Matches declared use",
			"Passt zum angegebenen Verwendungszweck",
		),
		mismatch: t(
			"Does not match declared use",
			"Passt nicht zum angegebenen Verwendungszweck",
		),
	};
	return (
		<section className="lp-scenario-block">
			<h3>
				{t(
					"Manufacturer terminal mapping",
					"Zuordnung der Herstelleranschlüsse",
				)}
			</h3>
			<p>
				{t(
					"Each end was checked separately against the manufacturer's terminal information available at review. This does not establish compatibility between the ends or approve the circuit or installation.",
					"Jedes Ende wurde einzeln anhand der zum Prüfzeitpunkt verfügbaren Herstellerangaben zum Anschluss geprüft. Dadurch werden weder die Kompatibilität der Enden noch die Freigabe des Stromkreises oder der Installation bestätigt.",
				)}
			</p>
			{review.circuits.map((c) => (
				<section key={c.circuit_id}>
					<h4>{c.name}</h4>
					{c.communication_use && (
						<p>
							{t(
								"Declared circuit use",
								"Angegebener Verwendungszweck des Stromkreises",
							)}
							: {communicationUseLabel(c.communication_use, locale)}
						</p>
					)}
					{c.endpoints.map((end) => {
						const instance = plan.instances.find(
							(d) => d.id === end.instance_id,
						);
						const point = instance?.ports.find((p) => p.id === end.port_id);
						return (
							<article key={end.side}>
								<h5>
									{end.side === "start" ? t("From", "Von") : t("To", "Nach")} ·{" "}
									{instance?.name ?? end.instance_id} ·{" "}
									{point?.name ?? end.port_id}
								</h5>
								<p>{status[end.status]}</p>
								{end.binding && (
									<p>
										{t("Selected terminal", "Ausgewählter Anschluss")}:{" "}
										{end.binding.terminal} · {end.binding.fact_id}
									</p>
								)}
								{end.fact && (
									<p>
										{locale.startsWith("de")
											? end.fact.label.de
											: end.fact.label.en}{" "}
										·{" "}
										{terminalDomainLabel(
											end.fact.specification.terminal_domain,
											locale,
										)}
										{end.fact.specification.terminal_use
											? ` · ${communicationUseLabel(end.fact.specification.terminal_use, locale)}`
											: ""}
									</p>
								)}
								<p>
									{t("Terminal domain", "Anschlussbereich")}:{" "}
									{domain[end.domain_status]}
								</p>
								<p>
									{t("Communication use", "Kommunikationszweck")}:{" "}
									{use[end.use_status]}
								</p>
								{end.fact ? (
									<CableSource source={end.fact.source} locale={locale} />
								) : (
									end.binding && (
										<details>
											<summary>
												{t(
													"Saved source reference",
													"Gespeicherter Quellenverweis",
												)}
											</summary>
											<p>
												{t("Product", "Produkt")}: {end.binding.product_id} ·{" "}
												{t("Product revision", "Produktrevision")}:{" "}
												<RevisionCode value={end.binding.product_revision} />
											</p>
											<p>
												{t("Document", "Dokument")}:{" "}
												<RevisionCode value={end.binding.document_id} /> ·{" "}
												{t("Document revision", "Dokumentrevision")}:{" "}
												<RevisionCode value={end.binding.document_revision} />
											</p>
										</details>
									)
								)}
							</article>
						);
					})}
				</section>
			))}
		</section>
	);
}
