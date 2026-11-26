import type { JsonObject } from "../data/protocol.ts";
import { energyGoal } from "./energyGoal.ts";
import { equipmentDraft, type EquipmentUse } from "./equipment.ts";
import { hasPlant, readPlantDraft } from "./equipmentPlant.ts";
function hasStorageDemand(setup: JsonObject): boolean {
	return (
		setup.operating_mode === "backup" ||
		[setup.required_usable_kwh, setup.required_discharge_ac_kw].some(
			(value) => typeof value === "number" && value > 0,
		)
	);
}

function hasBattery(setup: JsonObject): boolean {
	const use = setup.equipment_use as EquipmentUse | null | undefined;
	return (
		setup.battery_product_id !== null || (use != null && use.battery !== "new")
	);
}

export function hasStorageToExclude(inputs: JsonObject): boolean {
	if (energyGoal(inputs) === "backup" || inputs.equipment_demand !== undefined)
		return true;
	if (!hasPlant(inputs)) {
		const setup = equipmentDraft(inputs);
		return hasBattery(setup) || hasStorageDemand(setup);
	}
	const plant = readPlantDraft(inputs);
	return (
		hasStorageDemand(plant.requirements) ||
		plant.units.some(({ inputs }) => {
			const setup = equipmentDraft(inputs);
			return hasBattery(setup) || hasStorageDemand(setup);
		})
	);
}
