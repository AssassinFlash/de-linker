import type { ScenarioDraft } from "../../domain/energyScenario.ts";
import { __ } from "../../i18n.ts";

/** Operating-goal shortcuts update the same scenario as the chapter editor. */
export function SimpleEnergySetup({
	value,
	storageOnly,
	hasEquipment,
	chooseEquipment,
	disabled,
	onChange,
}: {
	value: ScenarioDraft;
	storageOnly: boolean;
	hasEquipment: boolean;
	chooseEquipment: () => void;
	disabled: boolean;
	onChange: (value: ScenarioDraft) => void;
}) {
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
		<fieldset disabled={disabled} className="sc-brief-fields">
			<section className="sc-work-panel">
				<h3 className="sc-work-panel-heading">
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
				<label className="sc-field">
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
					<button type="button" className="sc-button sc-primary" onClick={chooseEquipment}>
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
		</fieldset>
	);
}
