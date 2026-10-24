import type { ConverterDraft } from "../../domain/solarSetup.ts";
import type { PanelArray } from "../../domain/geometry.ts";
import { __, sprintf } from "../../i18n.ts";
import { ScenarioNumber } from "./ScenarioNumber.tsx";
import { ParameterNote } from "./ParameterNote.tsx";

/** Conversion bounds use Positive/Efficiency in pv-generation.schema.json.
 * PVWatts pdc0/eta parameters and the shared clipping stage are pinned in
 * docs/research/2026-10-24-pv-generation/WEATHER-AND-MODELS.md. */
export function PvConverterParameters({
	value,
	index,
	arrays,
	assignments,
	locale,
	report,
	onChange,
	remove,
	removeDisabled,
}: {
	value: ConverterDraft;
	index: number;
	arrays: readonly PanelArray[];
	assignments: ReadonlyMap<string, string>;
	locale: string;
	report: (field: string, valid: boolean) => void;
	onChange: (value: ConverterDraft) => void;
	remove: () => void;
	removeDisabled: boolean;
}) {
	return (
		<section className="lp-scenario-block lp-pv-parameters">
			<h4>{sprintf(__("Conversion group %d", "linker-tools"), index + 1)}</h4>
			<fieldset className="lp-pv-membership">
				<legend>{__("Arrays converted together", "linker-tools")}</legend>
				{arrays.map((array) => {
					const owner = assignments.get(array.id),
						selected = value.array_ids.includes(array.id);
					return (
						<label key={array.id} className="lp-pv-array-choice">
							<input
								type="checkbox"
								checked={selected}
								disabled={!!owner && owner !== value.id && !selected}
								onChange={(event) =>
									onChange({
										...value,
										array_ids: event.currentTarget.checked
											? [...value.array_ids, array.id]
											: value.array_ids.filter((id) => id !== array.id),
									})
								}
							/>
							<span>{array.name}</span>
						</label>
					);
				})}
			</fieldset>
			<div className="lp-geometry-fields">
				<ScenarioNumber
					field={value.id + "-reference"}
					label={__("PVWatts DC reference power", "linker-tools")}
					unit="W"
					locale={locale}
					value={value.reference_dc_power_w}
					report={report}
					onChange={(reference_dc_power_w) =>
						onChange({ ...value, reference_dc_power_w })
					}
				/>
				{(["eta_nominal", "eta_reference"] as const).map((field) => (
					<ScenarioNumber
						key={field}
						field={value.id + "-" + field}
						label={
							field === "eta_nominal"
								? __("Nominal conversion efficiency", "linker-tools")
								: __("PVWatts reference efficiency", "linker-tools")
						}
						unit="%"
						locale={locale}
						max={100}
						report={report}
						value={value[field] === null ? null : value[field] * 100}
						onChange={(number) =>
							onChange({
								...value,
								[field]: number === null ? null : number / 100,
							})
						}
					/>
				))}
			</div>
			<p>
				{__(
					"This reference power sets the PVWatts conversion curve; the model's AC output limit is reference power × nominal efficiency. It must be greater than zero. Array STC power and inverter hardware input limits are separate values. Both efficiencies must be greater than 0% and no more than 100%.",
					"linker-tools",
				)}
			</p>
			<ParameterNote
				label={__("Conversion-model source and assumptions", "linker-tools")}
				value={value.source_note}
				onChange={(source_note) => onChange({ ...value, source_note })}
			/>
			<button
				type="button"
				className="lp-text-button"
				onClick={remove}
				disabled={removeDisabled}
			>
				{__("Remove conversion group", "linker-tools")}
			</button>
		</section>
	);
}
