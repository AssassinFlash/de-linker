import { readObject } from "../../data/readProtocol.ts";
import type { CableQuantity } from "../../domain/installation.ts";
import { formatDecimal } from "../../domain/decimal.ts";
import { electricalText } from "./ElectricalConditionFields.tsx";

export function ConductorManufacturerResults({
	cables,
	locale,
}: {
	cables: readonly CableQuantity[];
	locale: string;
}) {
	const rows = cables.filter((cable) => cable.manufacturer_comparison);
	if (!rows.length) return null;
	const t = (en: string, de: string) => electricalText(locale, en, de);
	return (
		<section className="lp-scenario-block">
			<h3>
				{t(
					"Manufacturer conductor cross-section comparisons",
					"Herstellervergleich der Leiterquerschnitte",
				)}
			</h3>
			<p>
				{t(
					"Cable construction, protection and earthing require separate checks.",
					"Kabelaufbau, Schutz und Erdung müssen gesondert geprüft werden.",
				)}
			</p>
			{rows.map((cable) => {
				const comparison = cable.manufacturer_comparison!;
				const text =
					comparison.status === "within_recommendation"
						? t(
								"Within the recommended cross-section range",
								"Innerhalb des empfohlenen Querschnittsbereichs",
							)
						: comparison.status === "outside_recommendation"
							? t(
									"Outside the recommended cross-section range",
									"Außerhalb des empfohlenen Querschnittsbereichs",
								)
							: t(
									"Comparison unavailable; check the selection and confirmation",
									"Vergleich nicht verfügbar; Auswahl und Bestätigung prüfen",
								);
				const fact =
						comparison.fact === null ? null : readObject(comparison.fact),
					source = fact ? readObject(fact.source) : null,
					specification = fact ? readObject(fact.specification) : null,
					range = specification
						? readObject(specification.recommended_conductor_mm2)
						: null;
				return (
					<div key={cable.id} className="lp-selected-profile">
						<strong>{cable.name}</strong>
						{cable.conductor && (
							<p>
								{t("Declared cross-section", "Angegebener Querschnitt")}:{" "}
								{formatDecimal(cable.conductor.cross_section_mm2, locale)} mm²
							</p>
						)}
						{range &&
							typeof range.low === "number" &&
							typeof range.high === "number" && (
								<p>
									{t("Manufacturer range", "Herstellerbereich")}:{" "}
									{formatDecimal(range.low, locale)}–
									{formatDecimal(range.high, locale)} mm²
								</p>
							)}
						<p>{text}</p>
						{source && (
							<details>
								<summary>
									{t("Manufacturer source", "Herstellerquelle")}
								</summary>
								<a
									href={`${source.url}#page=${source.page}`}
									target="_blank"
									rel="noreferrer"
								>
									{t("Document · page", "Dokument · Seite")}{" "}
									{String(source.page)}
								</a>
								<blockquote>{String(source.quote)}</blockquote>
							</details>
						)}
					</div>
				);
			})}
		</section>
	);
}
