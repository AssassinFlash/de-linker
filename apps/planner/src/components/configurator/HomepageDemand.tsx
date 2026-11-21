import { useCallback } from "react";
import { readBrief } from "../../domain/brief.ts";
import type { Brief } from "../../domain/brief.ts";
import type { JsonObject } from "../../data/protocol.ts";
import { equipmentDraft } from "../../domain/equipment.ts";
import { hasPlant, readPlantDraft } from "../../domain/equipmentPlant.ts";
import { readScenarioDraft } from "../../domain/energyScenario.ts";
import { __ } from "../../i18n.ts";
import { retainsUnverifiedInverter } from "./ProjectEquipment.tsx";
import { NumberField } from "../NumberField.tsx";
import {
	changeBackupDemand,
	changeDemandEquipment,
	changePeakDemand,
	energyGoal,
} from "./EnergyDemand.tsx";
import {
	HomepagePvReference,
	changeHomepagePvPower,
	homepagePvReferenceAvailable,
} from "./HomepagePvReference.tsx";

function demands(inputs: JsonObject) {
	const equipment = hasPlant(inputs)
		? readPlantDraft(inputs).requirements
		: equipmentDraft(inputs);
	const backup = inputs.backup_demand as
		{ load_kw: number | null; duration_hours: number | null } | undefined;
	return { equipment, backup, goal: energyGoal(inputs) };
}

export function needsPreliminaryComparison(inputs: JsonObject) {
	const { equipment, backup } = demands(inputs);
	const demandReady =
		!!inputs.brief && hasComparisonDemand(inputs, readBrief(inputs.brief));
	if (backup && !demandReady) return true;
	return (
		equipment.grid_phase === null &&
		!(retainsUnverifiedInverter(inputs) && demandReady)
	);
}

export function hasComparisonDemand(inputs: JsonObject, brief: Brief) {
	const { backup, goal } = demands(inputs);
	const validBackup =
		backup &&
		typeof backup.load_kw === "number" &&
		backup.load_kw > 0 &&
		typeof backup.duration_hours === "number" &&
		backup.duration_hours > 0;
	return Boolean(
		brief.system_scope &&
		goal &&
		(brief.annual_load.kwh === null || brief.annual_load.basis !== null) &&
		(goal !== "backup" || (brief.system_scope !== "pv_only" && validBackup)),
	);
}

export function AnnualElectricityUse({
	brief,
	locale,
	edit,
	validity,
	requireSource = false,
}: {
	brief: Brief;
	locale: string;
	edit: (operation: (inputs: JsonObject) => JsonObject) => boolean;
	validity: (field: string, valid: boolean) => void;
	requireSource?: boolean;
}) {
	const annualValid = useCallback(
		(valid: boolean) => validity("annual", valid),
		[validity],
	);
	function annual(patch: Partial<Brief["annual_load"]>) {
		edit((current) => {
			const currentBrief = readBrief(current.brief);
			return {
				...current,
				brief: {
					...currentBrief,
					annual_load: { ...currentBrief.annual_load, ...patch },
				},
			};
		});
	}
	return (
		<>
			<NumberField
				name="annual_load_kwh"
				label={__("Annual electricity use", "linker-tools")}
				unit="kWh"
				locale={locale}
				min={0}
				value={brief.annual_load.kwh}
				onChange={(kwh) =>
					annual(kwh === null ? { kwh, basis: null } : { kwh })
				}
				onValidity={annualValid}
			/>
			{brief.annual_load.kwh !== null && (
				<label className="sc-field">
					<span>{__("Annual electricity use source", "linker-tools")}</span>
					<select
						name="annual_load_basis"
						required={requireSource}
						value={brief.annual_load.basis ?? ""}
						onChange={(event) => {
							const value = event.currentTarget.value;
							annual({
								basis:
									value === "bill_total" || value === "user_estimate"
										? value
										: null,
							});
						}}
					>
						<option value="">{__("Choose an option", "linker-tools")}</option>
						<option value="bill_total">
							{__("Electricity bill", "linker-tools")}
						</option>
						<option value="user_estimate">
							{__("Estimate", "linker-tools")}
						</option>
					</select>
				</label>
			)}
		</>
	);
}

export function HomepageDemand({
	inputs,
	brief,
	locale,
	addressLookup,
	usePvAddress,
	edit,
	validity,
}: {
	inputs: JsonObject;
	brief: Brief;
	locale: string;
	addressLookup: boolean;
	usePvAddress: boolean;
	edit: (operation: (inputs: JsonObject) => JsonObject) => boolean;
	validity: (field: string, valid: boolean) => void;
}) {
	const { equipment, backup, goal } = demands(inputs);
	const peak =
		inputs.energy_scenario === undefined
			? null
			: (readScenarioDraft(inputs.energy_scenario).schedule[0]?.import_cap_kw ??
				null);
	const coordinateValidity = useCallback(
		(valid: boolean) => validity("coordinates", valid),
		[validity],
	);
	const pvValid = useCallback(
		(valid: boolean) => validity("pv", valid),
		[validity],
	);
	const loadValid = useCallback(
		(valid: boolean) => validity("load", valid),
		[validity],
	);
	const durationValid = useCallback(
		(valid: boolean) => validity("duration", valid),
		[validity],
	);
	const peakValid = useCallback(
		(valid: boolean) => validity("peak", valid),
		[validity],
	);
	return (
		<div className="sc-fields">
			<label className="sc-field">
				<span>{__("Grid connection", "linker-tools")}</span>
				<select
					name="grid_phase"
					value={String(equipment.grid_phase ?? "")}
					onChange={(event) => {
						const value = event.currentTarget.value;
						const grid_phase = value === "1" ? 1 : value === "3" ? 3 : null;
						edit((current) => changeDemandEquipment(current, { grid_phase }));
					}}
				>
					<option value="">{__("Not yet known", "linker-tools")}</option>
					<option value="1">{__("Single phase", "linker-tools")}</option>
					<option value="3">{__("Three phase", "linker-tools")}</option>
				</select>
			</label>
			<AnnualElectricityUse
				brief={brief}
				locale={locale}
				edit={edit}
				validity={validity}
				requireSource
			/>
			{brief.system_scope &&
				brief.system_scope !== "storage_only" &&
				!hasPlant(inputs) && (
					<NumberField
						name="pv_dc_kw"
						label={__("PV array", "linker-tools")}
						unit="kWp"
						locale={locale}
						min={0}
						value={
							typeof equipment.pv_dc_kw === "number" ? equipment.pv_dc_kw : null
						}
						onChange={(pv_dc_kw) =>
							edit((current) =>
								changeHomepagePvPower(
									changeDemandEquipment(current, { pv_dc_kw }),
									pv_dc_kw,
								),
							)
						}
						onValidity={pvValid}
					/>
				)}
			{homepagePvReferenceAvailable(inputs, brief) && (
				<HomepagePvReference
					locale={locale}
					onCoordinateValidity={coordinateValidity}
					inputs={inputs}
					brief={brief}
					addressLookup={addressLookup}
					initialUseAddress={usePvAddress}
					power={
						typeof equipment.pv_dc_kw === "number" ? equipment.pv_dc_kw : null
					}
					edit={edit}
				/>
			)}
			{goal === "backup" && (
				<>
					<NumberField
						name="backup_load_kw"
						label={__("Backup load", "linker-tools")}
						unit="kW"
						locale={locale}
						min={0}
						value={backup?.load_kw ?? null}
						onChange={(value) =>
							edit((current) => changeBackupDemand(current, "load_kw", value))
						}
						onValidity={loadValid}
					/>
					<NumberField
						name="backup_duration_hours"
						label={__("Required duration", "linker-tools")}
						unit="h"
						locale={locale}
						min={0}
						value={backup?.duration_hours ?? null}
						onChange={(value) =>
							edit((current) =>
								changeBackupDemand(current, "duration_hours", value),
							)
						}
						onValidity={durationValid}
					/>
				</>
			)}
			{goal === "peak" && (
				<>
					<NumberField
						name="peak_import_kw"
						label={__("Target grid import limit", "linker-tools")}
						unit="kW"
						locale={locale}
						min={0}
						value={peak}
						onChange={(value) =>
							edit((current) => changePeakDemand(current, value))
						}
						onValidity={peakValid}
					/>
					<p className="sc-field-wide">
						{__(
							"To estimate peak reduction, provide a measured load profile and a target grid import limit. Without both, this comparison shows equipment options.",
							"linker-tools",
						)}
					</p>
				</>
			)}
		</div>
	);
}
