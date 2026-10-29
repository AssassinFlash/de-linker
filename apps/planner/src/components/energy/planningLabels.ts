import { isEnergyTask } from "../../data/readEnergyResult.ts";
import { REPORT_TASK } from "../../data/planningReport.ts";
import { __ } from "../../i18n.ts";
import type { RunState } from "../../data/planningProtocol.ts";
import { PV_TASK, WEATHER_TASK } from "../../data/readPreparationResult.ts";
import { SEARCH_TASK } from "../../data/equipmentSearch.ts";
import { EQUIPMENT_TASK } from "../../data/readEquipmentResult.ts";
import { PVGIS_REFERENCE_TASK } from "../../domain/pvgisReference.ts";
import { DIRECT_BEAM_TASK } from "../../domain/directBeam.ts";
import { GEOMETRIC_PV_TASK } from "../../domain/geometricPv.ts";

export function taskLabel(kind: string | null | undefined): string {
	if (kind === REPORT_TASK) return __("Planning report", "linker-tools");
	if (kind === SEARCH_TASK) return __("Equipment search", "linker-tools");
	if (kind === EQUIPMENT_TASK) return __("Equipment checks", "linker-tools");
	if (kind === WEATHER_TASK)
		return __("Weather data preparation", "linker-tools");
	if (kind === PV_TASK) return __("PV generation profile", "linker-tools");
	if (kind === GEOMETRIC_PV_TASK)
		return __("PV reference with roof shading", "linker-tools");
	if (kind === PVGIS_REFERENCE_TASK)
		return __("PVGIS annual AC reference", "linker-tools");
	if (kind === DIRECT_BEAM_TASK)
		return __("Geometric direct-beam visibility", "linker-tools");
	if (isEnergyTask(kind)) return __("Energy calculation", "linker-tools");
	return __("Saved task", "linker-tools");
}
export function runStateLabel(state: RunState, kind?: string | null): string {
	const preparing =
		kind === WEATHER_TASK ||
		kind === PV_TASK ||
		kind === PVGIS_REFERENCE_TASK ||
		kind === GEOMETRIC_PV_TASK;
	switch (state) {
		case "queued":
			return __("Queued", "linker-tools");
		case "running":
			if (kind === REPORT_TASK)
				return __("Preparing planning report…", "linker-tools");
			if (kind === SEARCH_TASK)
				return __("Searching for equipment combinations…", "linker-tools");
			if (kind === EQUIPMENT_TASK)
				return __("Checking equipment selection", "linker-tools");
			return preparing
				? __("Preparing source", "linker-tools")
				: __("Calculating", "linker-tools");
		case "retry_wait":
			return __("Waiting to retry", "linker-tools");
		case "succeeded":
			if (kind === REPORT_TASK) return __("Report ready", "linker-tools");
			if (kind === SEARCH_TASK)
				return __("Equipment search finished", "linker-tools");
			if (kind === EQUIPMENT_TASK)
				return __("Equipment check complete", "linker-tools");
			return preparing
				? __("Source ready", "linker-tools")
				: __("Calculation complete", "linker-tools");
		case "failed":
			return preparing
				? __("Source preparation failed", "linker-tools")
				: __("Calculation failed", "linker-tools");
		case "cancelled":
			return preparing
				? __("Source preparation cancelled", "linker-tools")
				: __("Calculation cancelled", "linker-tools");
	}
}
