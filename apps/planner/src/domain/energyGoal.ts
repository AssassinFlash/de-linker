import type { JsonObject } from "../data/protocol.ts";
import {
	emptyScenario,
	isStorageOnly,
	readScenarioDraft,
} from "./energyScenario.ts";
import { changeDemandEquipment } from "./equipmentPlant.ts";
export type EnergyGoal = "" | "self" | "backup" | "peak";
export function energyGoal(inputs: JsonObject): EnergyGoal {
	const scenario =
		inputs.energy_scenario === undefined
			? null
			: readScenarioDraft(inputs.energy_scenario);
	if (
		inputs.backup_demand !== undefined ||
		scenario?.schedule.some((period) => period.mode === "outage")
	)
		return "backup";
	if (scenario?.controller === "peak_shaving_with_reserve_v1") return "peak";
	return scenario?.schedule.some((period) => period.mode === "connected")
		? "self"
		: "";
}
export function changeEnergyGoal(
	inputs: JsonObject,
	goal: EnergyGoal,
): JsonObject {
	const scenario =
		inputs.energy_scenario === undefined
			? emptyScenario()
			: readScenarioDraft(inputs.energy_scenario);
	const { backup_demand, ...rest } = inputs;
	const leavingPeak =
		goal !== "peak" && scenario.controller === "peak_shaving_with_reserve_v1";
	return changeDemandEquipment(
		{
			...rest,
			...(goal === "backup"
				? {
						backup_demand: backup_demand ?? {
							schema_version: 1,
							load_kw: null,
							duration_hours: null,
						},
					}
				: {}),
			energy_scenario: {
				...scenario,
				controller:
					goal === "peak"
						? "peak_shaving_with_reserve_v1"
						: "self_consumption_with_reserve_v1",
				schedule: scenario.schedule.map((period) => ({
					...period,
					mode: goal === "backup" ? "outage" : goal ? "connected" : null,
					...(goal === "peak" ? { import_policy: "limited" } : {}),
					...(leavingPeak ? { import_policy: null, import_cap_kw: null } : {}),
					...(goal === "backup" ? { allow_grid_charge: false } : {}),
					...(goal && { pv_enabled: !isStorageOnly(inputs) }),
				})),
			},
		},
		{
			operating_mode:
				goal === "backup" ? "backup" : goal ? "grid_connected" : null,
		},
	);
}

export function changeBackupDemand(
	inputs: JsonObject,
	field: "load_kw" | "duration_hours",
	value: number | null,
): JsonObject {
	return {
		...inputs,
		backup_demand: {
			schema_version: 1,
			load_kw: null,
			duration_hours: null,
			...(inputs.backup_demand as JsonObject | undefined),
			[field]: value,
		},
	};
}

export function changePeakDemand(
	inputs: JsonObject,
	value: number | null,
): JsonObject {
	const scenario =
		inputs.energy_scenario === undefined
			? emptyScenario()
			: readScenarioDraft(inputs.energy_scenario);
	return {
		...inputs,
		energy_scenario: {
			...scenario,
			schedule: scenario.schedule.map((period) => ({
				...period,
				import_policy: "limited",
				import_cap_kw: value,
			})),
		},
	};
}
