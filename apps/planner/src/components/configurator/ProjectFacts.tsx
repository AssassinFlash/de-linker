import type { JsonObject } from "../../data/protocol.ts";
import { readBrief } from "../../domain/brief.ts";
import { formatDecimal } from "../../domain/decimal.ts";
import { __ } from "../../i18n.ts";

export function projectFacts(inputs: JsonObject, locale: string) {
	const facts: [string, string][] = [];
	const brief = inputs.brief ? readBrief(inputs.brief) : null;
	if (brief) {
		const country = brief.site.country_code;
		const location = [
			brief.site.location_label || brief.site.postal_code,
			country &&
				new Intl.DisplayNames([locale], { type: "region" }).of(country),
		]
			.filter(Boolean)
			.join(", ");
		if (location) facts.push([__("Location", "linker-tools"), location]);
		if (brief.project_use) {
			const uses = {
				residential: __("Residential", "linker-tools"),
				commercial: __("Commercial", "linker-tools"),
				industrial: __("Industrial", "linker-tools"),
			};
			facts.push([__("Site use", "linker-tools"), uses[brief.project_use]]);
		}
		if (brief.annual_load.kwh !== null)
			facts.push([
				__("Annual electricity use", "linker-tools"),
				formatDecimal(brief.annual_load.kwh, locale) + " kWh",
			]);
	}
	const panels = inputs.known_panel_details as JsonObject | undefined;
	if (panels) {
		if (typeof panels.count === "number")
			facts.push([
				__("Number of modules", "linker-tools"),
				formatDecimal(panels.count, locale),
			]);
		if (typeof panels.power_w === "number")
			facts.push([
				__("Power per panel", "linker-tools"),
				formatDecimal(panels.power_w, locale) + " Wp",
			]);
		if (typeof panels.system_kwp === "number")
			facts.push([
				__("Solar capacity", "linker-tools"),
				formatDecimal(panels.system_kwp, locale) + " kWp",
			]);
	}
	return facts;
}

export function ProjectFacts({ facts }: { facts: [string, string][] }) {
	return (
		<dl className="sc-project-facts">
			{facts.map(([label, value]) => (
				<div key={label}>
					<dt>{label}</dt>
					<dd>{value}</dd>
				</div>
			))}
		</dl>
	);
}
