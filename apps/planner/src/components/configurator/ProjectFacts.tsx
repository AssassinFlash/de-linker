import type { JsonObject } from "../../data/protocol.ts";
import { readBrief } from "../../domain/brief.ts";
import { equipmentDraft } from "../../domain/equipment.ts";
import { hasPlant, readPlantDraft } from "../../domain/equipmentPlant.ts";
import { readScenarioDraft } from "../../domain/energyScenario.ts";
import { energyGoal } from "../../domain/energyGoal.ts";
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
		if (brief.annual_load.basis)
			facts.push([
				__("Basis for the annual figure", "linker-tools"),
				brief.annual_load.basis === "bill_total"
					? __("Electricity bill", "linker-tools")
					: __("Estimate", "linker-tools"),
			]);
		if (brief.annual_load.source_note)
			facts.push([
				__("Source note", "linker-tools"),
				brief.annual_load.source_note,
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
	const equipment = hasPlant(inputs)
		? readPlantDraft(inputs).requirements
		: equipmentDraft(inputs);
	if (
		typeof equipment.pv_dc_kw === "number" &&
		typeof panels?.system_kwp !== "number"
	)
		facts.push([
			__("PV array size", "linker-tools"),
			formatDecimal(equipment.pv_dc_kw, locale) + " kWp",
		]);
	const goal = energyGoal(inputs);
	if (goal)
		facts.push([
			__("Main purpose", "linker-tools"),
			{
				self: __("Use more solar on site", "linker-tools"),
				backup: __("Backup supply", "linker-tools"),
				peak: __("Reduce peak demand", "linker-tools"),
			}[goal],
		]);
	if (goal || equipment.grid_phase != null)
		facts.push([
			__("Grid connection", "linker-tools"),
			equipment.grid_phase === 3
				? __("Three phase", "linker-tools")
				: equipment.grid_phase === 1
					? __("Single phase", "linker-tools")
					: __("To confirm", "linker-tools"),
		]);
	if (goal === "peak") {
		const limits = new Set(
			readScenarioDraft(inputs.energy_scenario).schedule.flatMap((period) =>
				period.mode === "connected" &&
				period.import_policy === "limited" &&
				period.import_cap_kw !== null
					? [formatDecimal(period.import_cap_kw, locale) + " kW"]
					: [],
			),
		);
		if (limits.size)
			facts.push([
				__("Target grid import limit", "linker-tools"),
				Array.from(limits).join(", "),
			]);
	}
	const backup = inputs.backup_demand as JsonObject | undefined;
	if (typeof backup?.load_kw === "number")
		facts.push([
			__("Backup load", "linker-tools"),
			formatDecimal(backup.load_kw, locale) + " kW",
		]);
	if (typeof backup?.duration_hours === "number")
		facts.push([
			__("Required duration", "linker-tools"),
			formatDecimal(backup.duration_hours, locale) + " h",
		]);
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

export function ProjectSummary({
	title,
	facts,
}: {
	title: string;
	facts: [string, string][];
}) {
	return (
		<aside
			className="sc-sidebar sc-project-summary"
			aria-label={__("Current configuration", "linker-tools")}
		>
			<section className="sc-card">
				<div>
					<p className="sc-eyebrow">
						{__("Current configuration", "linker-tools")}
					</p>
					<h3>{title}</h3>
				</div>
				<ProjectFacts facts={facts} />
			</section>
		</aside>
	);
}
