import { useCallback, useRef, useState } from "react";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { EquipmentPlant } from "../../domain/equipmentPlant.ts";
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
	openEquipment,
	client,
	scope,
	active,
	converters,
}: {
	value: PlantEnergyDraft;
	plant: EquipmentPlant;
	section: "storage" | "initial" | "operation";
	locale: string;
	disabled: boolean;
	onChange: (next: PlantEnergyDraft) => void;
	onValidity: (valid: boolean) => void;
	useProfileRange: () => void;
	rangeBusy: boolean;
	openEquipment: () => void;
	client: PlannerClient;
	scope: string;
	active: boolean;
	converters: readonly string[];
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
		<fieldset className="lp-scenario-fields" disabled={disabled}>
			{section === "storage" && (
				<label className="lp-field">
					<span>{__("PV connection for this plant", "linker-tools")}</span>
					<select
						disabled={!numbersValid}
						value={value.coupling ?? "plant_ac"}
						onChange={(e) =>
							onChange({
								...value,
								coupling: e.currentTarget.value as
									"plant_ac" | "plant_shared_dc",
							})
						}
					>
						<option value="plant_ac">
							{__("AC-coupled PV generation", "linker-tools")}
						</option>
						<option value="plant_shared_dc">
							{__("DC PV at individual storage converters", "linker-tools")}
						</option>
					</select>
				</label>
			)}
			<p className="lp-profile-help">
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
							className="lp-text-button"
							onClick={openEquipment}
						>
							{__("Review equipment selection", "linker-tools")}
						</button>
					</Notice>
				)}
			{section === "storage" && dcPlant && (
				<section className="lp-scenario-block">
					<h3>{__("PV groups at the common AC bus", "linker-tools")}</h3>
					<p className="lp-profile-help">
						{__(
							"Assign each roof PV group once: to one storage converter below or to the common AC bus here. Select the prepared roof PV source for this calculation. Any additional AC generation profile must represent a different source.",
							"linker-tools",
						)}
					</p>
					{converters.map((id) => (
						<label className="lp-field" key={id}>
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
				<label className="lp-field">
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
			)}
			{section === "storage" && (
				<div key={hardware.id}>
					{dcPlant ? (
						<>
							<label className="lp-field">
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
										{__("PV group connected to the DC inputs", "linker-tools")}
									</option>
									<option value="unused">
										{__("DC PV inputs unused", "linker-tools")}
									</option>
								</select>
							</label>
							<label className="lp-field">
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
						<label className="lp-field">
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
					<DcStorageForm
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
						inverterId={hardware.selection.inverter_product_id}
						storageOnly={!dcPlant}
						showPvAssignment={unit.pv_dc_input_unused !== true}
					/>
				</div>
			)}
			{section === "initial" && (
				<div key={hardware.id}>
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
					<label className="lp-field">
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
				<section className="lp-scenario-block">
					<OperatingPeriodsForm
						periods={value.schedule}
						onChange={(schedule) => onChange({ ...value, schedule })}
						locale={locale}
						report={report}
						useProfileRange={useProfileRange}
						rangeBusy={rangeBusy}
						perUnitReserve
					/>
					<p className="lp-profile-help">
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
					<p className="lp-profile-help">
						{__(
							"These results describe the declared scenario. Joint operating capability, continuous equipment performance, backup transfer and country-specific grid compliance are not established by this calculation.",
							"linker-tools",
						)}
					</p>
				</section>
			)}
		</fieldset>
	);
}
