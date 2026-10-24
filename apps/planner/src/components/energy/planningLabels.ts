import { __ } from "../../i18n.ts";
import type { RunState } from "../../data/planningProtocol.ts";
import { PV_TASK, WEATHER_TASK } from "../../data/readPreparationResult.ts";

export function taskLabel(kind: string | null | undefined): string {
	if (kind === WEATHER_TASK)
		return __("Weather data preparation", "linker-tools");
	if (kind === PV_TASK) return __("PV generation profile", "linker-tools");
	if (kind === "single_ac_energy_replay_v1")
		return __("Energy calculation", "linker-tools");
	return __("Saved task", "linker-tools");
}
export function runStateLabel(state: RunState, kind?: string | null): string {
	const preparing = kind === WEATHER_TASK || kind === PV_TASK;
	switch (state) {
		case "queued":
			return __("Queued", "linker-tools");
		case "running":
			return preparing
				? __("Preparing source", "linker-tools")
				: __("Calculating", "linker-tools");
		case "retry_wait":
			return __("Waiting to retry", "linker-tools");
		case "succeeded":
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
