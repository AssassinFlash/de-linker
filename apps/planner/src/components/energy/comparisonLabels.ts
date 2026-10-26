import { __ } from "../../i18n.ts";

export function comparisonLabel(id: string): string {
	const labels: Record<string, string> = {
		site: __("Site and time zone", "linker-tools"),
		periods: __("Calculated periods", "linker-tools"),
		demand_sources: __("Load and auxiliary sources", "linker-tools"),
		pv_weather: __("PV weather or identical generation input", "linker-tools"),
		time_resolution: __("Time resolution", "linker-tools"),
		operating_requirements: __("Operating requirements", "linker-tools"),
		starting_inventory: __("Starting stored energy", "linker-tools"),
		terminal_requirement: __("Required final stored energy", "linker-tools"),
		load_scope: __("Load measurement scope", "linker-tools"),
		calculation_method: __("Calculation method", "linker-tools"),
		scenario_constraints: __("Scenario requirements", "linker-tools"),
		battery_temperature: __("Battery temperature", "linker-tools"),
		storage_parameters: __("Storage parameters", "linker-tools"),
		equipment_selection: __("Equipment selection", "linker-tools"),
		pv_design: __("PV layout and generation settings", "linker-tools"),
		dc_auxiliary: __("DC auxiliary demand", "linker-tools"),
		capacity_basis: __("Capacity model differs", "linker-tools"),
		load_demand: __("Simulated load demand", "linker-tools"),
		solar_supply: __("Solar supplied to load", "linker-tools"),
		grid_import: __("Grid import", "linker-tools"),
		unserved_load: __("Unserved simulated load", "linker-tools"),
		pv_export: __("PV export", "linker-tools"),
		stored_final: __("Stored energy at end", "linker-tools"),
		pv_generation: __("PV generation", "linker-tools"),
		solar_share: __("Solar share of gross demand", "linker-tools"),
		pv_use: __("PV used or stored on site", "linker-tools"),
		matched: __("Match", "linker-tools"),
		different: __("Differ", "linker-tools"),
		unavailable: __("Not established", "linker-tools"),
	};
	return labels[id] ?? id;
}
