import type { JsonObject, Project } from "../../data/protocol.ts";
import { readObject } from "../../data/readProtocol.ts";
import { __ } from "../../i18n.ts";

export function PreparationBasis({
	weather,
	project,
	pv,
}: {
	weather: JsonObject;
	project: Project;
	pv: boolean;
}) {
	const request = readObject(weather.weather_request),
		interpretation = readObject(weather.weather_interpretation),
		details = readObject(
			readObject(readObject(weather.weather).source).details,
		),
		provenance = readObject(weather.provenance);
	return (
		<section className="lp-comparison">
			<dl className="lp-run-facts">
				<dt>{__("Weather source", "linker-tools")}</dt>
				<dd>
					{String(provenance.label)} · PVGIS {String(request.api_version)}
				</dd>
				<dt>{__("Radiation database", "linker-tools")}</dt>
				<dd>{String(details.radiation_database)}</dd>
				<dt>{__("Meteorological database", "linker-tools")}</dt>
				<dd>{String(details.meteo_database)}</dd>
				<dt>{__("Requested source year range", "linker-tools")}</dt>
				<dd>
					{String(request.start_year)} / {String(request.end_year)}
				</dd>
				<dt>{__("Synthetic calculation year", "linker-tools")}</dt>
				<dd>{String(interpretation.synthetic_energy_year)}</dd>
			</dl>
			<p>
				{__(
					"A typical meteorological year combines selected months from different years.",
					"linker-tools",
				)}
			</p>
			{pv && (
				<p>
					{__(
						"The PV profile includes reconstructed interval averages. Shorter output intervals do not increase the time resolution of the original weather data.",
						"linker-tools",
					)}
				</p>
			)}
			<details className="lp-comparison">
				<summary>
					{__("Original source and interpretation record", "linker-tools")}
				</summary>
				<pre>
					{JSON.stringify(
						{
							weather_request: request,
							weather_interpretation: interpretation,
							source: details,
							provenance,
						},
						null,
						2,
					)}
				</pre>
				{pv && (
					<>
						<h4>{__("PV model settings", "linker-tools")}</h4>
						<pre>{JSON.stringify(project.inputs.pv_generation, null, 2)}</pre>
					</>
				)}
			</details>
		</section>
	);
}
