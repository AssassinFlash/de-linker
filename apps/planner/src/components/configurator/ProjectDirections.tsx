import { useCallback, useRef } from "react";
import type { Configuration } from "../../data/config.ts";
import type { JsonObject } from "../../data/protocol.ts";
import type { ComparisonDraft } from "../../data/comparisonDraft.ts";
import { readBrief } from "../../domain/brief.ts";
import { equipmentDraft } from "../../domain/equipment.ts";
import { invalidateEnergyReplay } from "../../domain/energyScenario.ts";
import { __ } from "../../i18n.ts";
import { Icon } from "../Icon.tsx";
import { NumberField } from "../NumberField.tsx";
import { AnnualElectricityUse } from "./HomepageDemand.tsx";
import {
	changeDemandEquipment,
	changeEnergyGoal,
	energyGoal,
	type EnergyGoal,
} from "./EnergyDemand.tsx";
import { changeHomepagePvPower } from "./HomepagePvReference.tsx";

const scenes = ["new", "known", "retrofit", "commercial"] as const;
type Scene = NonNullable<ComparisonDraft["scene"]>;

export function ProjectDirections({
	selectedScene,
	changeScene,
	inputs,
	config,
	disabled,
	edit,
	validity,
	title,
	changeTitle,
	roof,
	compare,
	details,
}: {
	selectedScene: Scene | null;
	changeScene: (scene: Scene) => void;
	inputs: JsonObject;
	config: Pick<Configuration, "countries" | "locale">;
	disabled: boolean;
	edit: (fn: (current: JsonObject) => JsonObject) => boolean;
	validity: (field: string, valid: boolean) => void;
	title: string;
	changeTitle: (value: string) => void;
	roof: () => void;
	compare?: (() => void) | undefined;
	details?: (() => void) | undefined;
}) {
	const brief = readBrief(inputs.brief);
	const fields = useRef<HTMLFieldSetElement>(null);
	const pv = equipmentDraft(inputs).pv_dc_kw;
	const pvValid = useCallback(
		(valid: boolean) => validity("pv", valid),
		[validity],
	);
	const scene =
		selectedScene ??
		(() => {
			if (brief.system_scope === "storage_addition") return "retrofit";
			if (
				brief.project_use === "commercial" ||
				brief.project_use === "industrial"
			)
				return "commercial";
			if (typeof pv === "number") return "known";
			return brief.system_scope === "new_pv_storage" ? "new" : null;
		})();
	const labels = {
		new: __("New PV + storage", "linker-tools"),
		known: __("Known PV size", "linker-tools"),
		retrofit: __("Storage retrofit", "linker-tools"),
		commercial: __("Commercial & large-scale", "linker-tools"),
	};
	const descriptions = {
		new: __(
			"Plan panels, an inverter and a battery for a new site.",
			"linker-tools",
		),
		known: __("Start with the solar capacity in kWp.", "linker-tools"),
		retrofit: __(
			"Add a battery to the panels already on site.",
			"linker-tools",
		),
		commercial: __(
			"Compare equipment for a business or multi-system site.",
			"linker-tools",
		),
	};
	const icons = {
		new: "solar",
		known: "overview",
		retrofit: "layers",
		commercial: "system",
	} as const;
	function pick(selected: Scene) {
		const applied = edit((current) => {
			const source = readBrief(current.brief);
			return {
				...current,
				brief: {
					...source,
					system_scope:
						selected === "retrofit" ? "storage_addition" : "new_pv_storage",
					project_use:
						selected === "commercial" ? "commercial" : source.project_use,
				},
			};
		});
		if (applied) {
			changeScene(selected);
			if (selected === "known")
				fields.current
					?.querySelector<HTMLInputElement>('[name="site_pv_kw"]')
					?.focus();
		}
	}
	return (
		<>
			<fieldset className="sc-card sc-direction-start" disabled={disabled}>
				<legend>{__("What are you planning?", "linker-tools")}</legend>
				<div className="sc-scene-grid">
					{scenes.map((key) => (
						<button
							key={key}
							type="button"
							className="sc-scene"
							aria-label={labels[key]}
							aria-pressed={key === scene}
							onClick={() => pick(key)}
						>
							<Icon name={icons[key]} />
							<span>{labels[key]}</span>
							<small>{descriptions[key]}</small>
						</button>
					))}
				</div>
			</fieldset>
			<fieldset
				ref={fields}
				className="sc-card sc-direction-fields"
				disabled={disabled}
			>
				<legend>{__("Project details (optional)", "linker-tools")}</legend>
				<div className="sc-fields">
					<label className="sc-field">
						<span>{__("Project name", "linker-tools")}</span>
						<input
							name="project_name"
							maxLength={256}
							value={title}
							onChange={(e) => changeTitle(e.currentTarget.value)}
						/>
					</label>
					<label className="sc-field">
						<span>{__("Country", "linker-tools")}</span>
						<select
							name="project_country"
							value={brief.site.country_code ?? ""}
							onChange={(event) => {
								const code = event.currentTarget.value || null;
								edit((current) => {
									const b = readBrief(current.brief);
									return {
										...invalidateEnergyReplay(current),
										brief: {
											...b,
											site: {
												...b.site,
												country_code: code,
												latitude: null,
												longitude: null,
												postal_code: null,
												timezone: null,
												coordinate_basis: "not_provided",
											},
										},
									};
								});
							}}
						>
							<option value="">{__("Choose a country", "linker-tools")}</option>
							{Object.entries(config.countries)
								.sort((a, b) => a[1].localeCompare(b[1], config.locale))
								.map(([code, name]) => (
									<option key={code} value={code}>
										{name}
									</option>
								))}
						</select>
					</label>
					<AnnualElectricityUse
						brief={brief}
						locale={config.locale}
						edit={edit}
						validity={validity}
					/>
					<NumberField
						name="site_pv_kw"
						label={__("PV array", "linker-tools")}
						unit="kWp"
						locale={config.locale}
						min={0}
						value={typeof pv === "number" ? pv : null}
						onValidity={pvValid}
						onChange={(value) =>
							edit((current) =>
								changeHomepagePvPower(
									changeDemandEquipment(current, { pv_dc_kw: value }),
									value,
								),
							)
						}
					/>
					<label className="sc-field">
						<span>{__("Grid connection", "linker-tools")}</span>
						<select
							name="grid_phase"
							value={String(equipmentDraft(inputs).grid_phase ?? "")}
							onChange={(event) => {
								const phase = event.currentTarget.value;
								edit((current) =>
									changeDemandEquipment(current, {
										grid_phase: phase === "1" ? 1 : phase === "3" ? 3 : null,
									}),
								);
							}}
						>
							<option value="">{__("Not specified", "linker-tools")}</option>
							<option value="1">{__("Single-phase", "linker-tools")}</option>
							<option value="3">{__("Three-phase", "linker-tools")}</option>
						</select>
					</label>
					<label className="sc-field">
						<span>{__("Main purpose", "linker-tools")}</span>
						<select
							name="project_purpose"
							value={energyGoal(inputs)}
							onChange={(event) => {
								const goal = event.currentTarget.value as EnergyGoal;
								edit((current) => changeEnergyGoal(current, goal));
							}}
						>
							<option value="">{__("Choose an option", "linker-tools")}</option>
							<option value="self">
								{__("Use more solar on site", "linker-tools")}
							</option>
							<option value="peak">
								{__("Reduce peak demand", "linker-tools")}
							</option>
							<option
								value="backup"
								disabled={brief.system_scope === "pv_only"}
							>
								{__("Backup supply", "linker-tools")}
							</option>
						</select>
					</label>
				</div>
				<div className="callout-row sc-roof-callout">
					<div>
						<strong>{__("Roof studio", "linker-tools")}</strong>
						<p>
							{__(
								"Draw the roof to check how many panels fit.",
								"linker-tools",
							)}
						</p>
					</div>
					<button
						className="sc-button btn-secondary"
						type="button"
						onClick={roof}
					>
						{__("Open roof studio", "linker-tools")} <Icon name="arrow" />
					</button>
				</div>
				{compare && (
					<button
						type="button"
						className="sc-button sc-primary"
						onClick={compare}
					>
						{__("Compare systems", "linker-tools")}
					</button>
				)}
				{details && (
					<button
						type="button"
						className="sc-button btn-ghost"
						onClick={details}
					>
						{__("Enter project details", "linker-tools")}
					</button>
				)}
			</fieldset>
		</>
	);
}
