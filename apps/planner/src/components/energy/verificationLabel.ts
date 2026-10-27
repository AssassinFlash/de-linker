import { __ } from "../../i18n.ts";

/** Scenario-facing labels for the actual verifier's named constraints. Machine
 * references remain available in numerical details for reproducibility. */
export function verificationLabel(code: string): string | null {
	switch (code) {
		case "load_supplied":
			return __("Simulated demand supplied", "linker-tools");
		case "aux_ac_supplied":
			return __("AC auxiliary demand supplied", "linker-tools");
		case "internal_aux_supplied":
			return __("Internal auxiliary demand supplied", "linker-tools");
		case "reserve_maintained":
			return __("Stored-energy reserve", "linker-tools");
		case "usable_capacity":
			return __("Usable stored-energy limit", "linker-tools");
		case "terminal_inventory":
			return __("Final stored-energy requirement", "linker-tools");
		case "charge_power":
			return __("AC charging-power limit", "linker-tools");
		case "discharge_power":
			return __("AC discharging-power limit", "linker-tools");
		default:
			return null;
	}
}
