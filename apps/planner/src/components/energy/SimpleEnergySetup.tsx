import { useCallback, useRef } from "react";
import type { ScenarioDraft } from "../../domain/energyScenario.ts";
import { BATTERY_FIELDS } from "../../domain/energyScenario.ts";
import { InitialInventoryForm } from "./InitialInventoryForm.tsx";
import { OperatingPeriodsForm } from "./OperatingPeriodsForm.tsx";
import { __ } from "../../i18n.ts";
import { ScenarioNumber } from "./ScenarioNumber.tsx";
import { batteryPresentation } from "./batteryPresentation.ts";
import { fromPercent, toPercent } from "../../domain/decimal.ts";

/** A short editor over the same physical scenario used by the advanced form. */
export function SimpleEnergySetup({
	value,
	storageOnly,
	hasAuxiliaryProfile,
	hasEquipment,
	chooseEquipment,
	locale,
	disabled,
	onChange,
	onValidity,
	useProfileRange,
	rangeBusy,
	inputErrors,
}: {
	value: ScenarioDraft;
	storageOnly: boolean;
	hasAuxiliaryProfile: boolean;
	hasEquipment: boolean;
	chooseEquipment: () => void;
	locale: string;
	disabled: boolean;
	onChange: (value: ScenarioDraft) => void;
	onValidity: (valid: boolean) => void;
	useProfileRange: () => void;
	rangeBusy: boolean;
	inputErrors?: readonly string[];
}) {
	const validity = useRef(new Map<string, boolean>());
	const report = useCallback(
		(key: string, valid: boolean) => {
			validity.current.set(key, valid);
			onValidity([...validity.current.values()].every(Boolean));
		},
		[onValidity],
	);
	const period = value.schedule[0]!;
	const purpose =
		period.mode === "outage"
			? "backup"
			: value.controller === "peak_shaving_with_reserve_v1"
				? "peak"
				: period.mode === "connected"
					? "self"
					: "";
	function choosePurpose(purpose: string) {
		if (!purpose) return;
		onChange({
			...value,
			controller:
				purpose === "peak"
					? "peak_shaving_with_reserve_v1"
					: "self_consumption_with_reserve_v1",
			schedule: [
				{
					...period,
					mode: purpose === "backup" ? "outage" : "connected",
					...(purpose === "peak" ? { import_policy: "limited" as const } : {}),
					...(storageOnly ? { pv_enabled: false } : {}),
					...(purpose === "backup" ? { allow_grid_charge: false } : {}),
				},
			],
		});
	}
	return (
		<fieldset disabled={disabled} className="lp-brief-fields lp-work-main">
			<section className="lp-work-panel">
				<h3 className="lp-work-panel-heading">
					{__("Energy use and storage", "linker-tools")}
				</h3>
				{storageOnly && (
					<p>
						{__(
							"Storage-only project · no PV generation or roof required.",
							"linker-tools",
						)}
					</p>
				)}
				<label className="lp-field">
					<span>{__("Operating goal", "linker-tools")}</span>
					<select
						value={purpose}
						onChange={(e) => choosePurpose(e.currentTarget.value)}
					>
						<option value="">{__("Choose an option", "linker-tools")}</option>
						<option value="self">
							{__("Self-consumption", "linker-tools")}
						</option>
						<option value="backup">
							{__("Backup during an outage", "linker-tools")}
						</option>
						<option value="peak">
							{__("Peak shaving · separate AC storage", "linker-tools")}
						</option>
					</select>
				</label>
				<p>
					{__(
						"Choose an equipment configuration, or enter parameters for a system you already know.",
						"linker-tools",
					)}
				</p>
				{!hasEquipment && (
					<button type="button" className="lp-button" onClick={chooseEquipment}>
						{__("Choose equipment", "linker-tools")}
					</button>
				)}
				{purpose === "backup" && (
					<p>
						{__(
							"Select a critical-load profile in Energy use. Set the outage period and declare whether a documented backup PV supply is available. The calculation reports any unmet demand.",
							"linker-tools",
						)}
					</p>
				)}
				{storageOnly && purpose === "self" && (
					<p>
						{__(
							"Without PV, this mode uses only the starting charge. Choose peak shaving to recharge from the grid below a defined cap.",
							"linker-tools",
						)}
					</p>
				)}
			</section>
			<details
				className="lp-comparison lp-work-panel"
				open={hasEquipment || value.battery.usable_window_kwh !== null}
			>
				<summary>{__("Storage parameters", "linker-tools")}</summary>
				<div className="lp-geometry-fields">
					{BATTERY_FIELDS.map((field) => {
						const p = batteryPresentation(field);
						return (
							<ScenarioNumber
								key={field}
								field={field}
								label={p.label}
								unit={p.unit}
								locale={locale}
								value={
									p.scale === 100
										? toPercent(value.battery[field])
										: value.battery[field]
								}
								{...(p.max === undefined ? {} : { max: p.max })}
								report={report}
								onChange={(number) =>
									onChange({
										...value,
										battery: {
											...value.battery,
											[field]: p.scale === 100 ? fromPercent(number) : number,
										},
										battery_binding: null,
									})
								}
							/>
						);
					})}
					{(!hasAuxiliaryProfile || value.aux_ac_kw != null) && (
						<ScenarioNumber
							field="aux"
							label={__("Constant AC auxiliary demand", "linker-tools")}
							value={value.aux_ac_kw ?? null}
							unit="kW"
							locale={locale}
							report={report}
							onChange={(aux_ac_kw) => onChange({ ...value, aux_ac_kw })}
						/>
					)}
				</div>
				<label className="lp-field">
					<span>
						{__("Source or assumption for storage parameters", "linker-tools")}
					</span>
					<textarea
						value={value.source_note}
						rows={2}
						onChange={(event) =>
							onChange({
								...value,
								source_note: event.currentTarget.value,
								battery_binding: null,
							})
						}
					/>
				</label>
			</details>
			<details className="lp-comparison lp-work-panel">
				<summary>{__("Starting charge and source", "linker-tools")}</summary>
				<InitialInventoryForm
					value={value.initial_inventory}
					onChange={(initial_inventory) =>
						onChange({ ...value, initial_inventory })
					}
					locale={locale}
					report={report}
				/>
			</details>
			<OperatingPeriodsForm
				periods={value.schedule}
				inputErrors={inputErrors}
				onChange={(schedule) => onChange({ ...value, schedule })}
				locale={locale}
				report={report}
				useProfileRange={useProfileRange}
				rangeBusy={rangeBusy}
			/>
			<section className="lp-work-panel">
				<label className="lp-field">
					<span>
						{__("Stored energy at the end of the calculation", "linker-tools")}
					</span>
					<select
						value={value.terminal_policy ?? ""}
						onChange={(event) =>
							onChange({
								...value,
								terminal_policy: (event.currentTarget.value ||
									null) as ScenarioDraft["terminal_policy"],
							})
						}
					>
						<option value="">{__("Choose an option", "linker-tools")}</option>
						<option value="none">
							{__("No minimum required", "linker-tools")}
						</option>
						<option value="minimum">
							{__("Specify a minimum", "linker-tools")}
						</option>
					</select>
				</label>
				{value.terminal_policy === "minimum" && (
					<ScenarioNumber
						field="terminal"
						label={__("Minimum final stored energy", "linker-tools")}
						value={value.terminal_min_kwh}
						unit="kWh"
						locale={locale}
						report={report}
						onChange={(terminal_min_kwh) =>
							onChange({ ...value, terminal_min_kwh })
						}
					/>
				)}
			</section>
		</fieldset>
	);
}
