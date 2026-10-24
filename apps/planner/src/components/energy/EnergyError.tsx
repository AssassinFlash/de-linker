import { ApiError } from "../../data/protocol.ts";
import { __ } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";

export function energyErrorText(error: unknown): string {
	const code = error instanceof ApiError ? error.code : "";
	switch (code) {
		case "scenario_profiles_required":
			return __(
				"The scenario needs gross-load, available-PV and separate AC auxiliary interval profiles.",
				"linker-tools",
			);
		case "battery_source_required":
			return __(
				"The storage parameters need a source or assumption note.",
				"linker-tools",
			);
		case "invalid_battery_parameters":
			return __(
				"Storage values need attention. Efficiencies must be greater than 0% and no more than 100%; other storage values must be zero or greater.",
				"linker-tools",
			);
		case "initial_inventory_required":
			return __(
				"The three starting-energy amounts and their basis are required. An empty starting inventory can be selected explicitly.",
				"linker-tools",
			);
		case "initial_inventory_exceeds_window":
			return __(
				"Initial stored energy exceeds the usable energy window.",
				"linker-tools",
			);
		case "terminal_condition_required":
			return __(
				"The final-inventory requirement needs a choice and, when applicable, a minimum value.",
				"linker-tools",
			);
		case "operating_period_incomplete":
			return __(
				"An operating period is incomplete. An outage also needs a critical-load profile.",
				"linker-tools",
			);
		case "period_offset_required":
			return __(
				"Period timestamps need a date, time and Z or a numeric UTC offset.",
				"linker-tools",
			);
		case "reserve_exceeds_window":
			return __(
				"Reserved energy exceeds the usable energy window.",
				"linker-tools",
			);
		case "grid_cap_required":
			return __(
				"A specified import or export cap needs its value in kW. Zero is allowed.",
				"linker-tools",
			);
		case "outage_grid_charge":
			return __(
				"Grid charging cannot be enabled during an outage.",
				"linker-tools",
			);
		case "battery_not_prepared":
			return __(
				"The storage settings have changed and need to be prepared again.",
				"linker-tools",
			);
		case "scenario_changed":
			return __(
				"The inputs changed before preparation finished. Your current draft remains open.",
				"linker-tools",
			);
		case "no_shared_profile_range":
			return __(
				"The required profiles have no shared time range.",
				"linker-tools",
			);
		case "service_draining":
			return __(
				"New calculations are temporarily unavailable. This request remains available for retry.",
				"linker-tools",
			);
		case "conflict":
			return __(
				"The saved revision or request has changed. The open inputs and original request are kept for review.",
				"linker-tools",
			);
		case "evaluation_revision_changed":
			return __(
				"A newer input revision is saved on the server. This request did not create a calculation. Reopen the project to review the saved inputs.",
				"linker-tools",
			);
		case "invalid_input":
		case "invalid_energy_inputs":
			return __(
				"The scenario could not be accepted. Profile coverage, operating periods and storage settings need review.",
				"linker-tools",
			);
		case "invalid_run_reply":
		case "invalid_run_result":
		case "invalid_run_metrics":
		case "invalid_run_page":
		case "unsupported_run_model":
		case "unsupported_run_assessment":
			return __(
				"This calculation reply could not be verified. Saved calculations and the original request remain available.",
				"linker-tools",
			);
		default:
			return __(
				"The request could not be confirmed. Your inputs remain open here.",
				"linker-tools",
			);
	}
}
export function EnergyError({ error }: { error: unknown }) {
	return error ? <Notice error>{energyErrorText(error)}</Notice> : null;
}
