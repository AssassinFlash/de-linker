import type { JsonObject } from "../../data/protocol.ts";
import { readObject } from "../../data/readProtocol.ts";
import {
	REFERENCE_CAPACITY,
	capacityReference,
} from "../../domain/dcEnergy.ts";
import { __ } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";

export function capacityReferenceText() {
	return __(
		"This reference calculation uses the selected product’s published usable energy as a fixed model window. The manufacturer’s test conditions are shown with the source. Choosing this mode does not establish that they are met. Ageing and changes in usable energy with temperature or charge/discharge rate are not modelled. Conversion and storage losses follow the separate scenario assumptions. Actual deliverable energy is not established.",
		"linker-tools",
	);
}

export function capacityReferenceTitle() {
	return __(
		"Reference scenario using the manufacturer’s usable energy",
		"linker-tools",
	);
}

export function CapacityReferenceNotice({ result }: { result: JsonObject }) {
	let reference = false;
	if (result.prepared_dc_parameters)
		reference =
			capacityReference(readObject(result.prepared_dc_parameters)) !== null;
	if (result.parameter_sources) {
		const pool = readObject(readObject(result.parameter_sources).pool);
		reference ||= Object.values(pool).some(
			(proof) => capacityReference(readObject(proof)) !== null,
		);
	}
	return reference ? (
		<Notice>
			<strong>{capacityReferenceTitle()}</strong>
			<p>{capacityReferenceText()}</p>
		</Notice>
	) : null;
}

export function CapacityReferenceBasis({
	parameters,
	locale,
}: {
	parameters: JsonObject;
	locale: string;
}) {
	const reference = capacityReference(parameters);
	if (!reference || reference.basis !== REFERENCE_CAPACITY) return null;
	const qualifier = reference.manufacturer_qualifier;
	const conditions =
		qualifier && typeof qualifier === "object" && !Array.isArray(qualifier)
			? readObject(readObject(qualifier).source_text ?? {})
			: {};
	const language = locale.startsWith("de") ? "de" : "en";
	return (
		<section className="lp-scenario-block">
			<h4>{capacityReferenceTitle()}</h4>
			<dl className="lp-field-summary">
				<div>
					<dt>{__("Manufacturer’s stated usable energy", "linker-tools")}</dt>
					<dd>
						{new Intl.NumberFormat(locale, {
							maximumSignificantDigits: 12,
						}).format(Number(reference.published_usable_energy_kwh))}{" "}
						kWh
					</dd>
				</div>
			</dl>
			{typeof conditions[language] === "string" && (
				<p className="lp-profile-help">{String(conditions[language])}</p>
			)}
		</section>
	);
}
