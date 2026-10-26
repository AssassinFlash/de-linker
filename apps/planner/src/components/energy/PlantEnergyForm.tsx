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
}) {
	const [selected, select] = useState(plant.units[0]!.id);
	const [numbersValid, setNumbersValid] = useState(true);
	const hardware =
		plant.units.find((u) => u.id === selected) ?? plant.units[0]!;
	const unit = value.units.find((u) => u.unit_id === hardware.id)!;
	const validity = useRef(new Map<string, boolean>());
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
			units: value.units.map((u) => (u.unit_id === next.unit_id ? next : u)),
		});
	return (
		<fieldset className="lp-scenario-fields" disabled={disabled}>
			<p className="lp-profile-help">
				{__(
					"This calculation uses one shared AC metering point. Stored energy and its origin, power limits and loss assumptions are kept separately for each storage unit.",
					"linker-tools",
				)}
			</p>
			{(plant.requirements.pv_dc_kw !== 0 ||
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
								{__("This converter's DC PV inputs are unused", "linker-tools")}
							</span>
						</span>
					</label>
					<DcStorageForm
						value={unit.settings}
						locale={locale}
						onChange={(settings) => change({ ...unit, settings })}
						report={reportUnit}
						converters={[]}
						equipmentSelected
						openEquipment={openEquipment}
						client={client}
						scope={scope}
						active={active}
						inverterId={hardware.selection.inverter_product_id}
						storageOnly
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
						{__(
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
