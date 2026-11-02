import { useMemo } from "react";
import type { Draft } from "../../domain/draft.ts";
import type { JsonObject } from "../../data/protocol.ts";
import { equipmentDraft } from "../../domain/equipment.ts";
import { readInstallation } from "../../domain/installation.ts";
import {
	changePvPlantStringUnit,
	readPvPlantStringPlan,
} from "../../domain/pvPlantStrings.ts";
import type { PlantUnitDraft } from "../../domain/equipmentPlant.ts";
import { PvStringSetup } from "./PvStringSetup.tsx";
import { Notice } from "../Notice.tsx";
import { __, sprintf } from "../../i18n.ts";

export function PlantPvStringSetup({
	draft,
	unit,
	units,
	edit,
	locale,
	disabled,
	onValidity,
}: {
	draft: Draft;
	unit: PlantUnitDraft;
	units?: readonly PlantUnitDraft[];
	edit: (change: (inputs: JsonObject) => JsonObject) => boolean;
	locale: string;
	disabled: boolean;
	onValidity: (valid: boolean) => void;
}) {
	const plant = useMemo(
		() =>
			draft.history.current.pv_plant_string_plan === undefined
				? null
				: readPvPlantStringPlan(draft.history.current.pv_plant_string_plan),
		[draft.history.current.pv_plant_string_plan],
	);
	const wiring = plant?.units.find((u) => u.unit_id === unit.id),
		plan = wiring?.plan ?? null;
	const equipment = equipmentDraft(unit.inputs),
		inverterId =
			typeof equipment.inverter_product_id === "number"
				? equipment.inverter_product_id
				: null;
	const preparedPlant = draft.history.current.equipment_plant as
		JsonObject | undefined;
	const preparedUnit = (preparedPlant?.units as JsonObject[] | undefined)?.find(
		(u) => u.id === unit.id,
	);
	const selection = (unit.inputs.equipment_selection ??
		preparedUnit?.selection) as JsonObject | undefined;
	const revisions = selection?.product_revisions as JsonObject | undefined;
	const revision =
		inverterId === null ? undefined : revisions?.[String(inverterId)];
	const saved = readInstallation(draft.baseline.inputs.installation);
	const chosen = saved.instances.find(
		(i) => i.id === wiring?.inverter_instance_id,
	);
	const instances = saved.instances.filter(
		(i) =>
			i.product_id === inverterId &&
			i.product_revision === revision &&
			!plant?.units.some(
				(u) => u.unit_id !== unit.id && u.inverter_instance_id === i.id,
			),
	);
	const unavailableModuleLabels = Object.fromEntries(
		(plant?.units ?? [])
			.filter((other) => other.unit_id !== unit.id)
			.flatMap((other) =>
				other.plan.strings.flatMap((string) =>
					string.module_ids.map((id) => [
						id,
						sprintf(
							__("Assigned to system %s", "linker-tools"),
							units?.find((candidate) => candidate.id === other.unit_id)
								?.name ?? other.unit_id,
						),
					]),
				),
			),
	);
	return (
		<>
			<PvStringSetup
				key={unit.id}
				draft={draft}
				edit={edit}
				inverterId={inverterId}
				locale={locale}
				disabled={disabled}
				onValidity={onValidity}
				controlled={{
					plan,
					scopeLabel: unit.name,
					unavailableModuleLabels,
					unavailableModuleIds: Object.keys(unavailableModuleLabels),
					change: (value) => {
						return edit((inputs) =>
							changePvPlantStringUnit(
								inputs,
								unit.id,
								value
									? {
											unit_id: unit.id,
											inverter_instance_id:
												wiring?.inverter_instance_id ?? null,
											plan: value,
										}
									: null,
							),
						);
					},
				}}
			/>
			{wiring && (
				<label className="lp-field">
					<span>
						{__("Inverter in the saved installation", "linker-tools")}
					</span>
					<select
						disabled={disabled}
						value={wiring.inverter_instance_id ?? ""}
						onChange={(e) => {
							const id = e.currentTarget.value || null;
							edit((inputs) =>
								changePvPlantStringUnit(inputs, unit.id, {
									...wiring,
									inverter_instance_id: id,
								}),
							);
						}}
					>
						<option value="">
							{__("No inverter linked to the installation", "linker-tools")}
						</option>
						{wiring.inverter_instance_id &&
							!instances.some((i) => i.id === wiring.inverter_instance_id) && (
								<option value={wiring.inverter_instance_id} disabled>
									{chosen?.name ?? wiring.inverter_instance_id} ·{" "}
									{__("Needs attention", "linker-tools")}
								</option>
							)}
						{instances.map((i) => (
							<option key={i.id} value={i.id}>
								{i.name} · {i.id}
							</option>
						))}
					</select>
				</label>
			)}
			{wiring && (
				<Notice>
					{__(
						"Electrical checks use this system's strings. Select its inverter from the saved installation to link the strings to recorded circuits.",
						"linker-tools",
					)}
				</Notice>
			)}
		</>
	);
}
