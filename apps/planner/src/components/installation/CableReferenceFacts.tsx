import type {
	CableReference,
	CableEvidence,
} from "../../data/cableReferences.ts";
import { formatDecimal } from "../../domain/decimal.ts";
import { electricalText } from "./ElectricalConditionFields.tsx";
/** Break opportunities preserve the complete revision text for reading and copying. */
export function RevisionCode({ value }: { value: string }) {
	return (
		<code>
			{value
				.match(/.{1,8}/g)
				?.flatMap((part, index) =>
					index === 0 ? [part] : [<wbr key={index} />, part],
				)}
		</code>
	);
}
export function cableReferenceLabel(
	reference: CableReference,
	locale: string,
): string {
	const display = [reference.brand.trim(), reference.model.trim()]
		.filter(Boolean)
		.join(" ");
	return (
		display ||
		`${electricalText(locale, "Cable reference", "Kabelreferenz")} ${reference.id} · ${electricalText(locale, "Product", "Produkt")} ${reference.canonical_product_id}`
	);
}
export function CableSource({
	source,
	locale,
}: {
	source: CableEvidence;
	locale: string;
}) {
	return (
		<details>
			<summary>
				{electricalText(locale, "Manufacturer source", "Herstellerquelle")}
			</summary>
			<a
				href={source.url + "#page=" + source.page}
				target="_blank"
				rel="noreferrer"
			>
				{electricalText(locale, "Document · page", "Dokument · Seite")}{" "}
				{source.page}
			</a>
			<blockquote>{source.quote}</blockquote>
			<p>
				{electricalText(locale, "Document revision", "Dokumentrevision")}:{" "}
				<RevisionCode value={source.document_revision} />
			</p>
		</details>
	);
}
export function CableReferenceFacts({
	reference,
	locale,
}: {
	reference: CableReference;
	locale: string;
}) {
	const f = reference.cable_facts,
		t = (en: string, de: string) => electricalText(locale, en, de),
		n = (v: number) => formatDecimal(v, locale);
	return (
		<section className="lp-scenario-block">
			<h4>{cableReferenceLabel(reference, locale)}</h4>
			<p>
				{n(f.cross_section_mm2)} mm² · {f.core_count}{" "}
				{f.core_count === 1 ? t("core", "Ader") : t("cores", "Adern")} ·{" "}
				{f.conductor_material} · {f.insulation}
			</p>
			<p>
				{t("Product revision", "Produktrevision")}:{" "}
				<RevisionCode value={reference.product_revision} />
			</p>
			<CableSource source={f.source} locale={locale} />
			<p>
				{t(
					"Only exactly matching temperature, current type, frequency and arrangement can be used. Missing data supplies no assumption.",
					"Nur genau passende Temperatur, Stromart, Frequenz und Anordnung sind verwendbar. Fehlende Daten liefern keine Annahmen.",
				)}
			</p>
			{f.parameter_sets.length === 0 && (
				<p>
					{t(
						"No resistance parameter set published.",
						"Kein Widerstandsparametersatz veröffentlicht.",
					)}
				</p>
			)}
			{f.parameter_sets.map((p) => (
				<div key={p.id}>
					<strong>{p.id}</strong>
					<p>
						{p.current_kind.toUpperCase()} · {n(p.temperature_c)} °C · R{" "}
						{n(p.resistance_ohm_per_km)} Ω/km ·{" "}
						{p.resistance_basis === "maximum"
							? t("Maximum resistance", "Maximaler Widerstand")
							: t("Nominal resistance", "Nennwiderstand")}
						{p.frequency_hz !== null ? ` · ${n(p.frequency_hz)} Hz` : ""}
						{p.reactance_ohm_per_km !== null
							? ` · X ${n(p.reactance_ohm_per_km)} Ω/km`
							: ""}
						{p.arrangement !== null ? ` · ${p.arrangement}` : ""}
					</p>
					<CableSource source={p.source} locale={locale} />
				</div>
			))}
		</section>
	);
}
