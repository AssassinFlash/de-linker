import type { BatteryField } from "../../domain/energyScenario.ts";
import { __ } from "../../i18n.ts";

// Form inputs and frozen results must present the same model units. The model
// stores efficiencies as fractions; only their presentation uses percentages.
export function batteryPresentation(field: BatteryField): {
	label: string;
	unit: "kWh" | "kW" | "%" | "1/h";
	scale: 1 | 100;
	max?: number;
} {
	switch (field) {
		case "usable_window_kwh":
			return {
				label: __("Usable stored energy", "linker-tools"),
				unit: "kWh",
				scale: 1,
			};
		case "charge_ac_kw":
			return {
				label: __("AC charging power", "linker-tools"),
				unit: "kW",
				scale: 1,
			};
		case "discharge_ac_kw":
			return {
				label: __("AC discharging power", "linker-tools"),
				unit: "kW",
				scale: 1,
			};
		case "eta_charge":
			return {
				label: __("Charging efficiency", "linker-tools"),
				unit: "%",
				scale: 100,
				max: 100,
			};
		case "eta_discharge":
			return {
				label: __("Discharging efficiency", "linker-tools"),
				unit: "%",
				scale: 100,
				max: 100,
			};
		case "internal_aux_kw":
			return {
				label: __("Internal auxiliary power", "linker-tools"),
				unit: "kW",
				scale: 1,
			};
		case "standing_loss_rate_per_hour":
			return {
				label: __("Standing-loss coefficient", "linker-tools"),
				unit: "1/h",
				scale: 1,
			};
	}
}
