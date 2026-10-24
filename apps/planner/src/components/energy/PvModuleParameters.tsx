import type { ModuleDraft } from "../../domain/solarSetup.ts";
import type { ModuleSpec } from "../../domain/geometry.ts";
import { __ } from "../../i18n.ts";
import { ScenarioNumber } from "./ScenarioNumber.tsx";
import { ParameterNote } from "./ParameterNote.tsx";

export function PvModuleParameters({
	value,
	specification,
	locale,
	report,
	onChange,
}: {
	value: ModuleDraft;
	specification: ModuleSpec | undefined;
	locale: string;
	report: (field: string, valid: boolean) => void;
	onChange: (value: ModuleDraft) => void;
}) {
	const source = value.source;
	return (
		<section className="lp-scenario-block lp-pv-parameters">
			<h4>
				{specification?.model ??
					__("Module specification outside the current layout", "linker-tools")}
			</h4>
			<ScenarioNumber
				field={value.module_spec_id + "-gamma"}
				label={__("Temperature coefficient of maximum power", "linker-tools")}
				unit="%/°C"
				locale={locale}
				min={null}
				report={report}
				value={
					value.gamma_pdc_per_c === null ? null : value.gamma_pdc_per_c * 100
				}
				onChange={(number) =>
					onChange({
						...value,
						gamma_pdc_per_c: number === null ? null : number / 100,
					})
				}
			/>
			<p>
				{__(
					"The coefficient gives the relative change in maximum DC power for each 1 °C change in cell temperature, referenced to 25 °C. For a datasheet value of -0.29%/°C, the field value is -0.29.",
					"linker-tools",
				)}
			</p>
			<label className="lp-field">
				<span>{__("Temperature-coefficient source", "linker-tools")}</span>
				<select
					value={source.kind ?? ""}
					onChange={(event) =>
						onChange({
							...value,
							source: {
								...source,
								kind: (event.currentTarget.value || null) as typeof source.kind,
							},
						})
					}
				>
					<option value="">{__("Choose a source", "linker-tools")}</option>
					<option value="user_declared">
						{__("User-declared values", "linker-tools")}
					</option>
					<option value="datasheet">
						{__("Referenced datasheet", "linker-tools")}
					</option>
				</select>
			</label>
			<ParameterNote
				label={__("Coefficient source and conditions", "linker-tools")}
				value={source.note}
				onChange={(note) => onChange({ ...value, source: { ...source, note } })}
			/>
			<details className="lp-comparison" open={source.kind === "datasheet"}>
				<summary>
					{__("Coefficient document reference", "linker-tools")}
				</summary>
				<p>
					{__(
						"A datasheet reference requires its URL, SHA-256 checksum and page number. This records the reference without downloading or verifying the document.",
						"linker-tools",
					)}
				</p>
				<label className="lp-field">
					<span>{__("Source document URL", "linker-tools")}</span>
					<input
						type="text"
						maxLength={4096}
						value={source.url ?? ""}
						onChange={(event) =>
							onChange({
								...value,
								source: { ...source, url: event.currentTarget.value || null },
							})
						}
					/>
				</label>
				<label className="lp-field">
					<span>{__("Source document SHA-256", "linker-tools")}</span>
					<input
						type="text"
						maxLength={64}
						value={source.document_sha256 ?? ""}
						onChange={(event) =>
							onChange({
								...value,
								source: {
									...source,
									document_sha256: event.currentTarget.value || null,
								},
							})
						}
					/>
				</label>
				<ScenarioNumber
					field={value.module_spec_id + "-page"}
					label={__("Source page", "linker-tools")}
					unit=""
					locale={locale}
					integer
					min={1}
					max={Number.MAX_SAFE_INTEGER}
					report={report}
					value={source.page}
					onChange={(page) =>
						onChange({ ...value, source: { ...source, page } })
					}
				/>
			</details>
		</section>
	);
}
