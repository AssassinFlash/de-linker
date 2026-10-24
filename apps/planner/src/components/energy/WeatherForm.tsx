import { useCallback, useRef, useState } from "react";
import type { WeatherDraft } from "../../domain/solarSetup.ts";
import type { GeometryDocument } from "../../domain/geometry.ts";
import { __ } from "../../i18n.ts";
import { ScenarioNumber } from "./ScenarioNumber.tsx";

/** The editable request and its interpretation remain project inputs, not an
 * external request made while a control changes. Only an explicit start sends it. */
export function WeatherForm({
	value,
	anchor,
	locale,
	disabled,
	onChange,
	onValidity,
}: {
	value: WeatherDraft;
	anchor: GeometryDocument["coordinate_system"]["anchor"];
	locale: string;
	disabled: boolean;
	onChange: (next: WeatherDraft) => void;
	onValidity: (valid: boolean) => void;
}) {
	const validity = useRef(new Map<string, boolean>());
	const [locationReset, setLocationReset] = useState(0);
	const report = useCallback(
		(field: string, valid: boolean) => {
			if (validity.current.get(field) === valid) return;
			validity.current.set(field, valid);
			onValidity([...validity.current.values()].every(Boolean));
		},
		[onValidity],
	);
	const request = value.request;
	return (
		<fieldset className="lp-scenario-fields" disabled={disabled}>
			<section className="lp-scenario-block">
				<h3>{__("Typical-year weather", "linker-tools")}</h3>
				<p>
					{__(
						"PVGIS builds a typical weather year from representative months in the selected source period. The saved result records the returned databases, selected months and how their timestamps are used.",
						"linker-tools",
					)}
				</p>
				<div className="lp-geometry-fields">
					<ScenarioNumber
						key={"latitude-" + locationReset}
						field="weather-latitude"
						label={__("Latitude", "linker-tools")}
						unit="°"
						value={request.latitude_deg}
						min={-90}
						max={90}
						locale={locale}
						report={report}
						onChange={(latitude_deg) =>
							onChange({ ...value, request: { ...request, latitude_deg } })
						}
					/>
					<ScenarioNumber
						key={"longitude-" + locationReset}
						field="weather-longitude"
						label={__("Longitude", "linker-tools")}
						unit="°"
						value={request.longitude_deg}
						min={-180}
						max={180}
						locale={locale}
						report={report}
						onChange={(longitude_deg) =>
							onChange({ ...value, request: { ...request, longitude_deg } })
						}
					/>
				</div>
				<button
					type="button"
					className="lp-text-button"
					disabled={!anchor}
					onClick={() => {
						if (anchor) {
							// This explicit replacement also discards unfinished coordinate
							// text when the underlying numeric value already matches.
							setLocationReset((value) => value + 1);
							onChange({
								...value,
								request: {
									...request,
									latitude_deg: anchor.latitude_deg,
									longitude_deg: anchor.longitude_deg,
								},
							});
						}
					}}
				>
					{__("Use roof coordinates", "linker-tools")}
				</button>
				<p className="lp-profile-help">
					{__(
						"The roof reference point can supply WGS 84 coordinates. A postcode alone does not locate the roof.",
						"linker-tools",
					)}
				</p>
				<div className="lp-geometry-fields">
					<ScenarioNumber
						field="weather-start-year"
						integer
						label={__("First source year", "linker-tools")}
						unit=""
						value={request.start_year}
						min={1}
						max={9998}
						locale={locale}
						report={report}
						onChange={(start_year) =>
							onChange({ ...value, request: { ...request, start_year } })
						}
					/>
					<ScenarioNumber
						field="weather-end-year"
						integer
						label={__("Last source year", "linker-tools")}
						unit=""
						value={request.end_year}
						min={1}
						max={9998}
						locale={locale}
						report={report}
						onChange={(end_year) =>
							onChange({ ...value, request: { ...request, end_year } })
						}
					/>
				</div>
				<p className="lp-profile-help">
					{__(
						"PVGIS selects representative months from this period. Use whole calendar years. Availability depends on the location and database.",
						"linker-tools",
					)}
				</p>
				<label className="lp-field">
					<span>{__("Expected radiation database", "linker-tools")}</span>
					<select
						value={request.expected_radiation_database ?? ""}
						onChange={(event) =>
							onChange({
								...value,
								request: {
									...request,
									expected_radiation_database:
										event.currentTarget.value === ""
											? null
											: (event.currentTarget.value as
													"PVGIS-SARAH3" | "PVGIS-ERA5"),
								},
							})
						}
					>
						<option value="">{__("Choose…", "linker-tools")}</option>
						<option value="PVGIS-SARAH3">PVGIS-SARAH3</option>
						<option value="PVGIS-ERA5">PVGIS-ERA5</option>
					</select>
				</label>
				<p className="lp-profile-help">
					{__(
						"PVGIS chooses the radiation database for the location. This field checks that choice; it does not change it. Meteorological data must come from ERA5.",
						"linker-tools",
					)}
				</p>
				<label className="lp-field">
					<span>{__("Terrain horizon", "linker-tools")}</span>
					<select
						value={
							request.use_terrain_horizon === null
								? ""
								: String(request.use_terrain_horizon)
						}
						onChange={(event) =>
							onChange({
								...value,
								request: {
									...request,
									use_terrain_horizon:
										event.currentTarget.value === ""
											? null
											: event.currentTarget.value === "true",
								},
							})
						}
					>
						<option value="">{__("Choose…", "linker-tools")}</option>
						<option value="true">
							{__("Include PVGIS terrain horizon", "linker-tools")}
						</option>
						<option value="false">
							{__("Omit terrain horizon", "linker-tools")}
						</option>
					</select>
				</label>
				<p className="lp-profile-help">
					{__(
						"A terrain horizon does not include nearby buildings, trees or roof obstacles.",
						"linker-tools",
					)}
				</p>
			</section>
			<section className="lp-scenario-block">
				<h3>{__("Calculation year", "linker-tools")}</h3>
				<ScenarioNumber
					field="weather-output-year"
					integer
					label={__("Synthetic calculation year", "linker-tools")}
					unit=""
					value={value.interpretation.synthetic_energy_year}
					min={1}
					max={9998}
					locale={locale}
					report={report}
					onChange={(synthetic_energy_year) =>
						onChange({
							...value,
							interpretation: {
								...value.interpretation,
								synthetic_energy_year,
							},
						})
					}
				/>
				<p className="lp-profile-help">
					{__(
						"A non-leap year places the 8,760 typical-year hours on a shared UTC timeline. Solar positions still use the original source dates and the provider's irradiance-time offset. The result is not a forecast for the chosen year.",
						"linker-tools",
					)}
				</p>
				<p>
					{__(
						"Preparation updates the open draft. Save project records the settings before a weather request can start. Selecting a returned weather source is a separate step.",
						"linker-tools",
					)}
				</p>
				<p>
					{__(
						"Preparing changed weather settings clears the previous weather selection. The energy scenario must then be prepared again. Saved sources and results remain in the project history.",
						"linker-tools",
					)}
				</p>
			</section>
		</fieldset>
	);
}
