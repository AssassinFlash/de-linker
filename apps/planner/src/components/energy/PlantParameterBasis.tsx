import type { JsonObject } from "../../data/protocol.ts";
import { readObject } from "../../data/readProtocol.ts";
import { DC_LOSS_FIELDS } from "../../domain/dcEnergy.ts";
import { __ } from "../../i18n.ts";
import { dcLossLabel } from "./DcStorageForm.tsx";
import { DcParameterSources } from "./DcParameterSources.tsx";

export function PlantParameterBasis({
	result,
	locale,
}: {
	result: JsonObject;
	locale: string;
}) {
	const plant = readObject(readObject(result.equipment_binding).plant);
	const sources = readObject(result.parameter_sources),
		pool = readObject(sources.pool);
	const entries = sources.units as readonly JsonObject[];
	const format = (v: unknown) =>
		typeof v === "number"
			? new Intl.NumberFormat(locale, { maximumSignificantDigits: 9 }).format(v)
			: "—";
	return (
		<div className="lp-plant-parameter-basis">
			{(plant.units as readonly JsonObject[]).map((unit) => {
				const entry = entries.find((u) => u.unit_id === unit.id)!;
				const proof = readObject(pool[String(entry.parameter_sha256)]),
					losses = readObject(proof.loss_scenario);
				return (
					<details className="lp-comparison" key={String(unit.id)}>
						<summary>{String(unit.name)}</summary>
						<p>{String(losses.source_note)}</p>
						<dl className="lp-field-summary">
							<div>
								<dt>{__("Connected battery port", "linker-tools")}</dt>
								<dd>{String(losses.battery_port_id)}</dd>
							</div>
							<div>
								<dt>
									{__("Battery temperature for this scenario", "linker-tools")}
								</dt>
								<dd>
									{losses.battery_temperature_c == null
										? __("Not specified", "linker-tools")
										: format(losses.battery_temperature_c) + " °C"}
								</dd>
							</div>
							<div>
								<dt>
									{__(
										"Usable storage capacity in this scenario",
										"linker-tools",
									)}
								</dt>
								<dd>{format(proof.usable_window_kwh)} kWh</dd>
							</div>
							{DC_LOSS_FIELDS.map((field) => (
								<div key={field}>
									<dt>{dcLossLabel(field)}</dt>
									<dd>
										{format(
											typeof losses[field] === "number" &&
												field.startsWith("eta_")
												? losses[field] * 100
												: losses[field],
										)}{" "}
										{field.startsWith("eta_")
											? "%"
											: field === "internal_aux_kw"
												? "kW"
												: "1/h"}
									</dd>
								</div>
							))}
						</dl>
						<DcParameterSources parameters={proof} locale={locale} />
					</details>
				);
			})}
		</div>
	);
}
