import { __ } from "../../i18n.ts";

export function equipmentStatus(status: unknown): string {
	return status === "satisfied"
		? __("Checked requirements met", "linker-tools")
		: status === "violated"
			? __("Requirements not met", "linker-tools")
			: __("Further checks required", "linker-tools");
}
export function equipmentCheckLabel(id: string): string {
	switch (id.split(":")[0]) {
		case "converter_identity":
			return __("Converter output", "linker-tools");
		case "grid_phase":
			return __("Grid phases", "linker-tools");
		case "pv_dc_input":
			return __("PV input power", "linker-tools");
		case "pv_electrical_topology":
			return __("PV strings and inputs", "linker-tools");
		case "manufacturer_pair":
			return __("Manufacturer pairing", "linker-tools");
		case "modules_per_stack":
			return __("Module count", "linker-tools");
		case "parallel_stacks":
			return __("Parallel arrangement", "linker-tools");
		case "required_accessory":
			return __("Required accessory", "linker-tools");
		case "battery_voltage":
			return __("Battery voltage", "linker-tools");
		case "battery_sales_unit":
			return __("Sales unit", "linker-tools");
		case "usable_energy":
			return __("Usable energy", "linker-tools");
		case "continuous_battery_ac_output":
			return __("Continuous AC discharge power", "linker-tools");
		case "battery_discharge_path":
			return __("Battery discharge path", "linker-tools");
		case "backup_mode":
			return __("Backup transfer", "linker-tools");
		case "integrated_sales_unit":
			return __("Integrated storage system", "linker-tools");
		case "accessory_quantity":
			return __("Accessory quantity", "linker-tools");
		default:
			return __("Equipment checks", "linker-tools");
	}
}
export function equipmentReason(reason: string): string | null {
	if (reason === "disjoint_voltage_windows")
		return __("The documented voltage ranges do not overlap.", "linker-tools");
	if (reason === "partial_voltage_window_energy_not_established")
		return __(
			"The voltage ranges overlap only partly. The usable storage energy for this connection has not been established.",
			"linker-tools",
		);
	if (reason === "cited_topology_voltage_missing")
		return __(
			"This configuration requires a documented operating voltage range.",
			"linker-tools",
		);
	return null;
}
