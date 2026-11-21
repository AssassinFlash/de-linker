import { useCallback, useRef, useState } from "react";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { PlantEnergyEquipment } from "../../domain/plantEnergy.ts";
import type {
	PlantEnergyDraft,
	PlantEnergyUnitDraft,
} from "../../domain/plantEnergy.ts";
import { __ } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { DcStorageForm } from "./DcStorageForm.tsx";
import { InitialInventoryForm } from "./InitialInventoryForm.tsx";
import { OperatingPeriodsForm } from "./OperatingPeriodsForm.tsx";
import { ScenarioNumber } from "./ScenarioNumber.tsx";

/** One common meter, with state and source-bound parameters for each device. */
export function PlantEnergyForm({
	value,
	plant,
	section,
	locale,
	disabled,
	onChange,
	onValidity,
	useProfileRange,
	rangeBusy,
	inputErrors,
	openEquipment,
	client,
	scope,
	active,
	converters,
	referenceCapacitySupported = false,
	storageOnly = false,
	sharedDcOnly = false,
}: {
	value: PlantEnergyDraft;
	plant: PlantEnergyEquipment;
	section: "storage" | "initial" | "operation";
	locale: string;
	disabled: boolean;
	onChange: (next: PlantEnergyDraft) => void;
	onValidity: (valid: boolean) => void;
	useProfileRange: () => void;
	rangeBusy: boolean;
	inputErrors?: readonly string[];
	openEquipment: () => void;
	client: PlannerClient;
	scope: string;
	active: boolean;
	converters: readonly string[];
	referenceCapacitySupported?: boolean;
	storageOnly?: boolean;
	sharedDcOnly?: boolean;
}) {
	const [selected, select] = useState(plant.units[0]!.id);
	const [numbersValid, setNumbersValid] = useState(true);
	const hardware =
		plant.units.find((u) => u.id === selected) ?? plant.units[0]!;
	const unit = value.units.find((u) => u.unit_id === hardware.id)!;
	const validity = useRef(new Map<string, boolean>());
	const dcPlant = value.coupling === "plant_shared_dc";
	const report = useCallback(
		(field: string, valid: boolean) => {
			validity.current.set(field, valid);
			const validNow = [...validity.current.values()].every(Boolean);
			setNumbersValid(validNow);
			onValidity(validNow);
		},
		[onValidity],
	);
	const reportUnit = useCallback(
		(field: string, valid: boolean) => report(`${hardware.id}:${field}`, valid),
		[hardware.id, report],
	);
	const change = (next: PlantEnergyUnitDraft) =>
		onChange({
			...value,
			ac_pv_converter_ids:
				next.pv_dc_input_unused === false && next.settings.dc?.pv_converter_id
					? (value.ac_pv_converter_ids ?? []).filter(
							(id) => id !== next.settings.dc!.pv_converter_id,
						)
					: (value.ac_pv_converter_ids ?? []),
			units: value.units.map((u) => (u.unit_id === next.unit_id ? next : u)),
		});
	return (
		<fieldset className="sc-scenario-fields sc-work-main" disabled={disabled}>
			<section className="sc-work-panel" hidden={section !== "storage"}>
				<h3 className="sc-work-panel-heading">
					{__("System connection", "linker-tools")}
				</h3>
				{section === "storage" && !sharedDcOnly && (
					<label className="sc-field">
						<span>{__("PV connection for this plant", "linker-tools")}</span>
						<select
							disabled={!numbersValid}
							value={value.coupling ?? "plant_ac"}
							onChange={(e) =>
								onChange({
									...value,
									coupling: e.currentTarget.value as
										"plant_ac" | "plant_shared_dc",
									...(e.currentTarget.value === "plant_shared_dc"
										? {
												controller:
													"proportional_available_power_self_consumption_v1" as const,
												aux_ac_kw: null,
											}
										: {}),
								})
							}
						>
							<option value="plant_ac">
								{__("AC-coupled PV generation", "linker-tools")}
							</option>
							<option value="plant_shared_dc" disabled={storageOnly}>
								{__("DC PV at individual storage converters", "linker-tools")}
							</option>
						</select>
					</label>
				)}
				<p className="sc-field-help">
					{__(
						"This calculation uses one shared AC metering point. Stored energy and its origin, power limits and loss assumptions are kept separately for each storage unit.",
						"linker-tools",
					)}
				</p>
				{!dcPlant &&
					(plant.requirements.pv_dc_kw !== 0 ||
						plant.units.some((u) => u.selection.pv_dc_kw !== 0)) && (
						<Notice>
							{__(
								"This calculation includes PV only through a separate AC generation input. In the storage plan, set the total DC PV nameplate rating and each converter's DC PV allocation to zero. Confirm that every storage converter's DC PV inputs are unused.",
								"linker-tools",
							)}
							<button
								type="button"
								className="sc-text-button"
								onClick={openEquipment}
							>
								{__("Review equipment selection", "linker-tools")}
							</button>
						</Notice>
					)}
			</section>
			{section === "storage" && dcPlant && (
				<section className="sc-scenario-block sc-work-panel">
					<h3 className="sc-work-panel-heading">
						{__("PV groups at the common AC bus", "linker-tools")}
					</h3>
					<p className="sc-field-help">
						{__(
							"Assign each roof PV group once: to one storage converter below or to the common AC bus here. Select the prepared roof PV source for this calculation. Any additional AC generation profile must represent a different source.",
							"linker-tools",
						)}
					</p>
					{converters.map((id) => (
						<label className="sc-field" key={id}>
							<span>
								<input
									type="checkbox"
									checked={(value.ac_pv_converter_ids ?? []).includes(id)}
									disabled={value.units.some(
										(u) =>
											u.pv_dc_input_unused === false &&
											u.settings.dc?.pv_converter_id === id,
									)}
									onChange={(e) =>
										onChange({
											...value,
											ac_pv_converter_ids: e.currentTarget.checked
												? [...(value.ac_pv_converter_ids ?? []), id]
												: (value.ac_pv_converter_ids ?? []).filter(
														(key) => key !== id,
													),
										})
									}
								/>
								<span>{id}</span>
							</span>
						</label>
					))}
					{converters.length === 0 && (
						<p>
							{__(
								"No roof PV groups are available to assign yet.",
								"linker-tools",
							)}
						</p>
					)}
				</section>
			)}
			{section !== "operation" && (
				<div className="sc-work-panel sc-work-toolbar">
					<label className="sc-field">
						<span>{__("Storage unit", "linker-tools")}</span>
						<select
							disabled={!numbersValid}
							value={hardware.id}
							onChange={(e) => select(e.currentTarget.value)}
						>
							{plant.units.map((u) => (
								<option key={u.id} value={u.id}>
									{u.name}
								</option>
							))}
						</select>
					</label>
				</div>
			)}
			{section === "storage" && (
				<div key={hardware.id} className="sc-work-main">
					<section className="sc-work-panel">
						<h3 className="sc-work-panel-heading">
							{__("Storage unit", "linker-tools")} · {hardware.name}
						</h3>
						{dcPlant ? (
							<>
								<label className="sc-field">
									<span>
										{__("PV connection on this converter", "linker-tools")}
									</span>
									<select
										value={
											unit.pv_dc_input_unused === null
												? ""
												: unit.pv_dc_input_unused
													? "unused"
													: "connected"
										}
										onChange={(e) =>
											change({
												...unit,
												pv_dc_input_unused:
													e.currentTarget.value === ""
														? null
														: e.currentTarget.value === "unused",
											})
										}
									>
										<option value="">
											{__("Choose an option", "linker-tools")}
										</option>
										<option value="connected">
											{__(
												"PV group connected to the DC inputs",
												"linker-tools",
											)}
										</option>
										<option value="unused">
											{__("DC PV inputs unused", "linker-tools")}
										</option>
									</select>
								</label>
								<label className="sc-field">
									<span>
										{__("Charging from the common AC bus", "linker-tools")}
									</span>
									<select
										value={
											unit.allow_ac_charge == null
												? ""
												: unit.allow_ac_charge
													? "enabled"
													: "disabled"
										}
										onChange={(e) =>
											change({
												...unit,
												allow_ac_charge:
													e.currentTarget.value === ""
														? null
														: e.currentTarget.value === "enabled",
											})
										}
									>
										<option value="">
											{__("Choose an option", "linker-tools")}
										</option>
										<option value="disabled">
											{__("Disabled", "linker-tools")}
										</option>
										<option value="enabled">
											{__(
												"Enabled (requires documented AC-to-DC charging)",
												"linker-tools",
											)}
										</option>
									</select>
								</label>
							</>
						) : (
							<label className="sc-field">
								<span>
									<input
										type="checkbox"
										checked={unit.pv_dc_input_unused === true}
										onChange={(e) =>
											change({
												...unit,
												pv_dc_input_unused: e.currentTarget.checked,
											})
										}
									/>
									<span>
										{__(
											"This converter's DC PV inputs are unused",
											"linker-tools",
										)}
									</span>
								</span>
							</label>
						)}
					</section>
					<DcStorageForm
						referenceCapacitySupported={referenceCapacitySupported}
						value={unit.settings}
						locale={locale}
						onChange={(settings) => change({ ...unit, settings })}
						report={reportUnit}
						converters={converters}
						equipmentSelected
						openEquipment={openEquipment}
						client={client}
						scope={scope}
						active={active}
						inverterId={
							typeof hardware.selection.inverter_product_id === "number"
								? hardware.selection.inverter_product_id
								: null
						}
						storageOnly={!dcPlant}
						showPvAssignment={unit.pv_dc_input_unused !== true}
					/>
				</div>
			)}
			{section === "initial" && (
				<div key={hardware.id} className="sc-work-panel">
					<InitialInventoryForm
						value={unit.settings.initial_inventory}
						onChange={(initial_inventory) =>
							change({
								...unit,
								settings: { ...unit.settings, initial_inventory },
							})
						}
						locale={locale}
						report={reportUnit}
					/>
					<ScenarioNumber
						field="unit-reserve"
						label={__("Reserved stored energy", "linker-tools")}
						value={unit.reserve_kwh}
						unit="kWh"
						locale={locale}
						report={reportUnit}
						onChange={(reserve_kwh) => change({ ...unit, reserve_kwh })}
					/>
					<label className="sc-field">
						<span>
							{__(
								"Stored energy at the end of the calculation",
								"linker-tools",
							)}
						</span>
						<select
							value={unit.settings.terminal_policy ?? ""}
							onChange={(e) =>
								change({
									...unit,
									settings: {
										...unit.settings,
										terminal_policy: (e.currentTarget.value || null) as
											"none" | "minimum" | null,
									},
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
					{unit.settings.terminal_policy === "minimum" && (
						<ScenarioNumber
							field="unit-terminal"
							label={__("Minimum final stored energy", "linker-tools")}
							value={unit.settings.terminal_min_kwh}
							unit="kWh"
							locale={locale}
							report={reportUnit}
							onChange={(terminal_min_kwh) =>
								change({
									...unit,
									settings: { ...unit.settings, terminal_min_kwh },
								})
							}
						/>
					)}
				</div>
			)}
			{section === "operation" && (
				<section className="sc-scenario-block sc-work-main">
					{!dcPlant && (
						<section className="sc-work-panel">
							<h3 className="sc-work-panel-heading">
								{__("Operating strategy", "linker-tools")}
							</h3>
							<label className="sc-field">
								<span>{__("Operating strategy", "linker-tools")}</span>
								<select
									value={
										value.controller ??
										"proportional_available_power_self_consumption_v1"
									}
									onChange={(e) =>
										onChange({
											...value,
											controller: e.currentTarget.value as NonNullable<
												PlantEnergyDraft["controller"]
											>,
											schedule: value.schedule.map((p) => ({
												...p,
												...(e.currentTarget.value ===
												"proportional_peak_shaving_v1"
													? { import_policy: "limited" as const }
													: {}),
											})),
										})
									}
								>
									<option value="proportional_available_power_self_consumption_v1">
										{__("Self-consumption with reserve", "linker-tools")}
									</option>
									<option value="proportional_peak_shaving_v1">
										{__("Peak shaving · separate AC storage", "linker-tools")}
									</option>
								</select>
							</label>
							<p>
								{__(
									"Peak shaving charges from the grid only when grid charging is allowed and import headroom remains. Discharge covers demand above the cap; during outages it supplies the critical load.",
									"linker-tools",
								)}
							</p>
							<label className="sc-field">
								<span>
									<input
										type="checkbox"
										checked={value.aux_ac_kw != null}
										onChange={(e) =>
											onChange({
												...value,
												aux_ac_kw: e.currentTarget.checked ? 0 : null,
											})
										}
									/>{" "}
									{__(
										"Use constant AC auxiliary demand instead of a profile",
										"linker-tools",
									)}
								</span>
							</label>
							{value.aux_ac_kw != null && (
								<ScenarioNumber
									field="aux-ac"
									label={__("Constant AC auxiliary demand", "linker-tools")}
									value={value.aux_ac_kw}
									unit="kW"
									locale={locale}
									report={report}
									onChange={(aux_ac_kw) => onChange({ ...value, aux_ac_kw })}
								/>
							)}
						</section>
					)}
					<OperatingPeriodsForm
						periods={value.schedule}
						inputErrors={inputErrors}
						inputPath="energy_plant_setup.schedule"
						onChange={(schedule) => onChange({ ...value, schedule })}
						locale={locale}
						report={report}
						useProfileRange={useProfileRange}
						rangeBusy={rangeBusy}
						perUnitReserve
					/>
					<details className="sc-disclosure sc-work-panel">
						<summary>{__("How storage is operated", "linker-tools")}</summary>
						<p className="sc-field-help">
							{dcPlant
								? __(
										"In each interval, each converter supplies its own DC auxiliary demand and its allocated share of AC demand before charging from local DC PV. AC demand is shared in proportion to each unit’s available power. Charging from the AC bus must be enabled and supported by the equipment documentation. It uses remaining AC surplus; grid charging is requested only when separately permitted and within the remaining import limit. This time-step calculation uses no forecast and does not reproduce a manufacturer EMS or an optimal dispatch schedule.",
										"linker-tools",
									)
								: __(
										"Import and export limits apply once at the shared AC metering point. In each interval, charging or discharging is shared in proportion to each unit's available power within its declared power and energy limits. The rule uses no forecast, does not request grid charging and does not reproduce a manufacturer EMS or an optimal dispatch schedule.",
										"linker-tools",
									)}
						</p>
						<p className="sc-field-help">
							{__(
								"These results describe the declared scenario. Joint operating capability, continuous equipment performance, backup transfer and country-specific grid compliance are not established by this calculation.",
								"linker-tools",
							)}
						</p>
					</details>
				</section>
			)}
		</fieldset>
	);
}
