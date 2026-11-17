import { useCallback, useEffect, useState } from "react";
import type { JsonObject } from "../../data/protocol.ts";
import type { ScenarioDraft } from "../../domain/energyScenario.ts";
import { changeEquipment, equipmentDraft } from "../../domain/equipment.ts";
import { NumberField } from "../NumberField.tsx";
import { __ } from "../../i18n.ts";

/** Customer demand edits the project that the equipment search submits. */
export function ProjectEnergyDemand({
	inputs,
	scenario,
	locale,
	disabled,
	edit,
	changeScenario,
	compare,
	onValidity,
}: {
	inputs: JsonObject;
	scenario: ScenarioDraft;
	locale: string;
	disabled: boolean;
	edit: (operation: (inputs: JsonObject) => JsonObject) => boolean;
	changeScenario: (next: ScenarioDraft) => void;
	compare: () => void;
	onValidity: (valid: boolean) => void;
}) {
	const goal =
		scenario.schedule[0]?.mode === "outage"
			? "backup"
			: scenario.controller === "peak_shaving_with_reserve_v1"
				? "peak"
				: scenario.schedule[0]?.mode === "connected"
					? "self"
					: "";
	const demand = inputs.backup_demand as
		{ load_kw: number | null; duration_hours: number | null } | undefined;
	const equipment = equipmentDraft(inputs);
	const [loadValid, setLoadValid] = useState(true);
	const [durationValid, setDurationValid] = useState(true);
	useEffect(() => {
		onValidity(loadValid && durationValid);
		return () => onValidity(true);
	}, [loadValid, durationValid, onValidity]);
	const changeDemand = useCallback(
		(field: "load_kw" | "duration_hours", value: number | null) => {
			edit((current) => ({
				...current,
				backup_demand: {
					schema_version: 1,
					load_kw: null,
					duration_hours: null,
					...(current.backup_demand as JsonObject | undefined),
					[field]: value,
				},
			}));
		},
		[edit],
	);
	return (
		<fieldset className="lp-brief-fields" disabled={disabled}>
			<section className="lp-work-panel">
				<h2>{__("What should the system do?", "linker-tools")}</h2>
				<label className="lp-field">
					<span>{__("Operating goal", "linker-tools")}</span>
					<select
						value={goal}
						onChange={(event) => {
							const next = event.currentTarget.value;
							if (!next) return;
							changeScenario({
								...scenario,
								controller:
									next === "peak"
										? "peak_shaving_with_reserve_v1"
										: "self_consumption_with_reserve_v1",
								schedule: [
									{
										...scenario.schedule[0]!,
										mode: next === "backup" ? "outage" : "connected",
									},
								],
							});
							edit((current) => {
								const { backup_demand, ...rest } = current;
								return changeEquipment(next === "backup" ? current : rest, {
									operating_mode:
										next === "backup" ? "backup" : "grid_connected",
								});
							});
						}}
					>
						<option value="">{__("Choose an option", "linker-tools")}</option>
						<option value="self">
							{__("Use more solar on site", "linker-tools")}
						</option>
						<option value="backup">
							{__("Backup supply", "linker-tools")}
						</option>
						<option value="peak">
							{__("Reduce peak demand", "linker-tools")}
						</option>
					</select>
				</label>
				{goal === "peak" && (
					<NumberField
						label={__("Target grid import limit", "linker-tools")}
						unit="kW"
						locale={locale}
						min={0}
						value={scenario.schedule[0]?.import_cap_kw ?? null}
						onValidity={setLoadValid}
						onChange={(import_cap_kw) =>
							changeScenario({
								...scenario,
								schedule: [
									{
										...scenario.schedule[0]!,
										import_policy: "limited",
										import_cap_kw,
									},
								],
							})
						}
					/>
				)}
				{goal === "backup" && (
					<>
						<p>
							{__(
								"Which loads must keep running, and for how long?",
								"linker-tools",
							)}
						</p>
						<div className="lp-geometry-fields">
							<NumberField
								label={__("Backup load", "linker-tools")}
								unit="kW"
								locale={locale}
								min={0}
								value={demand?.load_kw ?? null}
								onChange={(value) => changeDemand("load_kw", value)}
								onValidity={setLoadValid}
							/>
							<NumberField
								label={__("Required duration", "linker-tools")}
								unit="h"
								locale={locale}
								min={0}
								value={demand?.duration_hours ?? null}
								onChange={(value) => changeDemand("duration_hours", value)}
								onValidity={setDurationValid}
							/>
						</div>
						<label className="lp-field">
							<span>{__("Grid connection", "linker-tools")}</span>
							<select
								value={(equipment.grid_phase as 1 | 3 | null) ?? ""}
								onChange={(event) => {
									const phase = event.currentTarget.value;
									edit((current) =>
										changeEquipment(current, {
											grid_phase: phase === "" ? null : phase === "1" ? 1 : 3,
										}),
									);
								}}
							>
								<option value="">
									{__("Choose an option", "linker-tools")}
								</option>
								<option value="1">{__("Single phase", "linker-tools")}</option>
								<option value="3">{__("Three phase", "linker-tools")}</option>
							</select>
						</label>
						<button
							type="button"
							className="lp-button"
							onClick={compare}
							disabled={
								!loadValid ||
								!durationValid ||
								!(demand?.load_kw && demand.load_kw > 0) ||
								!(demand?.duration_hours && demand.duration_hours > 0) ||
								equipment.grid_phase === null
							}
						>
							{__("Compare systems", "linker-tools")}
						</button>
					</>
				)}
			</section>
		</fieldset>
	);
}
