import type { ArrayDraft, ArrayFactor } from "../../domain/solarSetup.ts";
import { ARRAY_FACTORS } from "../../domain/solarSetup.ts";
import { __ } from "../../i18n.ts";
import { ScenarioNumber } from "./ScenarioNumber.tsx";
import { ParameterNote } from "./ParameterNote.tsx";

function factorLabel(field: ArrayFactor): string {
	switch (field) {
		case "albedo":
			return __("Ground reflectance", "linker-tools");
		case "beam_iam_b":
			return __("ASHRAE incidence-angle coefficient b", "linker-tools");
		case "sky_diffuse_iam_factor":
			return __("Retained sky-diffuse irradiance", "linker-tools");
		case "ground_diffuse_iam_factor":
			return __("Retained ground-reflected irradiance", "linker-tools");
		case "spectral_factor":
			return __("Spectral factor", "linker-tools");
		case "soiling_factor":
			return __("Irradiance retained after soiling", "linker-tools");
		case "dc_wiring_factor":
			return __("DC power retained after wiring losses", "linker-tools");
		case "dc_mismatch_factor":
			return __("DC power retained after mismatch losses", "linker-tools");
	}
}

/** Bounds mirror PvArrayParameters/SapmParameters in pv-generation.schema.json.
 * Models, units and factor stages follow the retained pinned pvlib source in
 * docs/research/2026-10-24-pv-generation/WEATHER-AND-MODELS.md. */
export function PvArrayParameters({
	value,
	name,
	locale,
	report,
	onChange,
}: {
	value: ArrayDraft;
	name: string;
	locale: string;
	report: (field: string, valid: boolean) => void;
	onChange: (value: ArrayDraft) => void;
}) {
	return (
		<section className="lp-scenario-block lp-pv-parameters">
			<h4>{name}</h4>
			<label className="lp-field">
				<span>{__("Irradiance transposition", "linker-tools")}</span>
				<select
					value={value.transposition ?? ""}
					onChange={(event) =>
						onChange({
							...value,
							transposition: (event.currentTarget.value ||
								null) as ArrayDraft["transposition"],
						})
					}
				>
					<option value="">{__("Choose a model", "linker-tools")}</option>
					<option value="isotropic">{__("Isotropic", "linker-tools")}</option>
					<option value="haydavies">Hay-Davies</option>
					<option value="perez">Perez</option>
					<option value="perez-driesse">Perez-Driesse</option>
				</select>
			</label>
			<p>
				{__(
					"Transposition estimates irradiance on each module plane using the saved roof and mounting orientation. Ground reflectance is the share reflected by the ground. The remaining percentage factors describe the share retained: 98% means a 2% reduction.",
					"linker-tools",
				)}
			</p>
			<div className="lp-geometry-fields">
				{ARRAY_FACTORS.map((field) => {
					const scale = field === "beam_iam_b" ? 1 : 100,
						number = value[field];
					return (
						<ScenarioNumber
							key={field}
							field={value.array_id + "-" + field}
							label={factorLabel(field)}
							unit={scale === 1 ? "1" : "%"}
							locale={locale}
							report={report}
							{...(scale === 1 ? {} : { max: 100 })}
							value={number === null ? null : number * scale}
							onChange={(number) =>
								onChange({
									...value,
									[field]: number === null ? null : number / scale,
								})
							}
						/>
					);
				})}
			</div>
			<ParameterNote
				label={__("Irradiance and loss assumptions", "linker-tools")}
				value={value.source_note}
				onChange={(source_note) => onChange({ ...value, source_note })}
			/>
			<details className="lp-comparison" open>
				<summary>{__("Cell temperature model", "linker-tools")}</summary>
				<p>
					{__(
						"SAPM estimates cell temperature from plane-of-array irradiance, air temperature and wind speed at 10 m. Its a, b and ΔT coefficients depend on module construction and mounting; ΔT is specified at 1000 W/m². No mounting preset is applied.",
						"linker-tools",
					)}
				</p>
				<div className="lp-geometry-fields">
					{(["a", "b", "delta_t_c"] as const).map((field) => (
						<ScenarioNumber
							key={field}
							field={value.array_id + "-thermal-" + field}
							label={
								field === "a"
									? __("SAPM coefficient a", "linker-tools")
									: field === "b"
										? __("SAPM coefficient b", "linker-tools")
										: __("Cell-to-module ΔT at 1000 W/m²", "linker-tools")
							}
							unit={field === "a" ? "1" : field === "b" ? "s/m" : "°C"}
							min={field === "delta_t_c" ? 0 : null}
							locale={locale}
							report={report}
							value={value.thermal[field]}
							onChange={(number) =>
								onChange({
									...value,
									thermal: { ...value.thermal, [field]: number },
								})
							}
						/>
					))}
				</div>
				<ParameterNote
					label={__(
						"Temperature-model source and mounting conditions",
						"linker-tools",
					)}
					value={value.thermal.source_note}
					onChange={(source_note) =>
						onChange({ ...value, thermal: { ...value.thermal, source_note } })
					}
				/>
			</details>
		</section>
	);
}
