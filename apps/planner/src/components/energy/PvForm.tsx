import { useCallback, useRef, useState } from "react";
import type { PvDraft } from "../../domain/solarSetup.ts";
import { alignPv, emptyConverter } from "../../domain/solarSetup.ts";
import type { GeometryDocument, PanelArray } from "../../domain/geometry.ts";
import { __, sprintf } from "../../i18n.ts";
import { ParameterNote } from "./ParameterNote.tsx";
import { PvModuleParameters } from "./PvModuleParameters.tsx";
import { PvArrayParameters } from "./PvArrayParameters.tsx";
import { PvConverterParameters } from "./PvConverterParameters.tsx";
import type { ModuleTemplate } from "../../data/moduleTemplates.ts";
import { matchesModule } from "../../data/moduleTemplates.ts";

export function PvForm({
	value,
	geometry,
	arrays,
	locale,
	disabled,
	valid,
	onChange,
	onValidity,
	moduleTemplates,
}: {
	value: PvDraft;
	geometry: GeometryDocument;
	arrays: readonly PanelArray[];
	locale: string;
	disabled: boolean;
	valid: boolean;
	onChange: (next: PvDraft) => void;
	onValidity: (valid: boolean) => void;
	moduleTemplates?: readonly ModuleTemplate[] | undefined;
}) {
	const [section, setSection] = useState<"modules" | "arrays" | "conversion">(
			"modules",
		),
		validity = useRef(new Map<string, boolean>());
	const report = useCallback(
		(field: string, accepted: boolean) => {
			if (validity.current.get(field) === accepted) return;
			validity.current.set(field, accepted);
			onValidity([...validity.current.values()].every(Boolean));
		},
		[onValidity],
	);
	const assignments = new Map(
		value.converters.flatMap((group) =>
			group.array_ids.map((id) => [id, group.id] as const),
		),
	);
	const moduleSelectionCurrent = [
		...new Set(arrays.map((array) => array.module_spec_id)),
	].every((id) => {
		const specification = geometry.module_specs.find(
			(module) => module.id === id,
		);
		return (
			!!specification &&
			!!moduleTemplates?.some((template) =>
				matchesModule(specification, template),
			)
		);
	});
	return (
		<fieldset className="lp-scenario-fields" disabled={disabled}>
			<section className="lp-scenario-block">
				<h3>{__("PV generation model", "linker-tools")}</h3>
				<p>
					{__(
						"This reference calculation estimates available AC generation from the saved roof layout and selected typical-year weather. It uses a uniform, unshaded array model implemented with pvlib. Site shading, string design, equipment suitability and country-specific approval need separate assessment.",
						"linker-tools",
					)}
				</p>
				<p>
					{sprintf(
						__("Active arrays in the current roof layout: %d.", "linker-tools"),
						arrays.length,
					)}
				</p>
				<button
					type="button"
					className="lp-button lp-button-secondary"
					disabled={
						!valid || moduleTemplates === undefined || !moduleSelectionCurrent
					}
					onClick={() => onChange(alignPv(value, geometry, moduleTemplates))}
				>
					{__("Update parameters for current roof layout", "linker-tools")}
				</button>
				<p>
					{__(
						"The update takes the temperature coefficient and its source from the current product selection. Other settings for matching arrays are kept; entries for arrays outside the layout are removed. New arrays need model settings and a conversion group.",
						"linker-tools",
					)}
				</p>
			</section>
			<ol className="lp-scenario-steps">
				{(["modules", "arrays", "conversion"] as const).map((step, index) => (
					<li key={step} aria-current={section === step ? "step" : undefined}>
						<button type="button" onClick={() => setSection(step)}>
							<span>{String(index + 1).padStart(2, "0")}</span>
							{step === "modules"
								? __("Modules", "linker-tools")
								: step === "arrays"
									? __("Array models", "linker-tools")
									: __("Power conversion", "linker-tools")}
						</button>
					</li>
				))}
			</ol>
			<div hidden={section !== "modules"}>
				{value.modules.length === 0 && (
					<p>
						{__(
							"Module parameter fields are created when the parameters are updated for the current roof layout.",
							"linker-tools",
						)}
					</p>
				)}
				{value.modules.map((module) => (
					<PvModuleParameters
						key={module.module_spec_id}
						value={module}
						specification={geometry.module_specs.find(
							(item) => item.id === module.module_spec_id,
						)}
						locale={locale}
					/>
				))}
			</div>
			<div hidden={section !== "arrays"}>
				{value.arrays.length === 0 && (
					<p>
						{__(
							"Array model fields are created when the parameters are updated for the current roof layout.",
							"linker-tools",
						)}
					</p>
				)}
				{value.arrays.map((array) => (
					<PvArrayParameters
						key={array.array_id}
						value={array}
						name={
							geometry.arrays.find((item) => item.id === array.array_id)
								?.name ?? __("Array outside the current layout", "linker-tools")
						}
						locale={locale}
						report={report}
						onChange={(next) =>
							onChange({
								...value,
								arrays: value.arrays.map((item) =>
									item.array_id === array.array_id ? next : item,
								),
							})
						}
					/>
				))}
			</div>
			<div hidden={section !== "conversion"}>
				<section className="lp-scenario-block">
					<h3>{__("Shared power conversion", "linker-tools")}</h3>
					<p>
						{__(
							"Each active array must belong to exactly one conversion group. The model sums each group's array DC power after the declared losses, then applies one shared PVWatts conversion curve and AC output limit. Each array is assumed to have independent maximum-power tracking. Electrical strings and physical inverter suitability need separate assessment.",
							"linker-tools",
						)}
					</p>
				</section>
				{value.converters.map((group, index) => (
					<PvConverterParameters
						key={group.id}
						value={group}
						index={index}
						arrays={arrays}
						assignments={assignments}
						locale={locale}
						report={report}
						onChange={(next) =>
							onChange({
								...value,
								converters: value.converters.map((item) =>
									item.id === group.id ? next : item,
								),
							})
						}
						remove={() => {
							if (valid)
								onChange({
									...value,
									converters: value.converters.filter(
										(item) => item.id !== group.id,
									),
								});
						}}
						removeDisabled={!valid}
					/>
				))}
				<button
					type="button"
					className="lp-button lp-button-secondary"
					disabled={!valid || arrays.length === 0}
					onClick={() =>
						onChange({
							...value,
							converters: [...value.converters, emptyConverter()],
						})
					}
				>
					{__("Add conversion group", "linker-tools")}
				</button>
			</div>
			<ParameterNote
				label={__("Overall PV model assumptions", "linker-tools")}
				value={value.source_note}
				onChange={(source_note) => onChange({ ...value, source_note })}
			/>
		</fieldset>
	);
}
