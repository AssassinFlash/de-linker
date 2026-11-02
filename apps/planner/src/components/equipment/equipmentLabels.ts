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
		case "plant_grid_phase":
			return __("Plant grid phases", "linker-tools");
		case "plant_operating_mode":
			return __("Plant operating mode", "linker-tools");
		case "plant_operating_scope":
			return __("Manufacturer requirement applicability", "linker-tools");
		case "plant_parallel_count":
			return __("Converters in the group", "linker-tools");
		case "plant_joint_operation":
			return __("Joint operation", "linker-tools");
		case "plant_controller_network_count":
			return __("Inverters on the controller network", "linker-tools");
		case "plant_controller":
			return __("Shared controller", "linker-tools");
		case "plant_pv_allocation":
			return __("Allocated PV nameplate rating", "linker-tools");
		case "plant_energy_allocation":
			return __("Allocated usable energy target", "linker-tools");
		case "plant_discharge_allocation":
			return __("Allocated continuous discharge power target", "linker-tools");
		case "plant_joint_energy":
			return __("Usable energy at the shared connection", "linker-tools");
		case "plant_joint_discharge":
			return __(
				"Continuous discharge power at the shared connection",
				"linker-tools",
			);
		case "pv_iv_model":
			return __("Single-diode model fit", "linker-tools");
		case "pv_model_applicability":
			return __("Model applicability to this module", "linker-tools");
		case "pv_operating_conditions":
			return __("Operating-condition domain", "linker-tools");
		case "pv_operating_curve":
			return __("Operating curve", "linker-tools");
		case "pv_hot_mppt":
			return __("Modeled MPP voltage: hot case", "linker-tools");
		case "pv_cold_mppt":
			return __("Modeled MPP voltage: cold case", "linker-tools");
		case "pv_hot_current":
			return __("Modeled MPPT current: hot case", "linker-tools");
		case "pv_cold_current":
			return __("Modeled MPPT current: cold case", "linker-tools");
		case "pv_hot_isc":
			return __("Modeled short-circuit current: hot case", "linker-tools");
		case "pv_cold_isc":
			return __("Modeled short-circuit current: cold case", "linker-tools");

		case "pv_parallel_count":
			return __("Strings per MPPT", "linker-tools");
		case "pv_layout_coverage":
			return __("Roof module assignment", "linker-tools");
		case "pv_tracker":
			return __("MPPT assignment", "linker-tools");
		case "pv_input":
			return __("Inverter input assignment", "linker-tools");
		case "pv_cold_voc":
			return __("Cold open-circuit voltage", "linker-tools");
		case "pv_module_voltage":
			return __("Module system voltage (IEC rating)", "linker-tools");
		case "pv_stc_mppt":
			return __("MPP voltage at STC", "linker-tools");
		case "pv_nameplate_layout":
			return __("Wired PV nameplate power", "linker-tools");
		case "pv_stc_current":
			return __("MPPT operating current at STC", "linker-tools");
		case "pv_stc_isc":
			return __("MPPT short-circuit current at STC", "linker-tools");
		case "pv_parallel_match":
			return __("Parallel string lengths and orientations", "linker-tools");
		case "pv_operating_temperatures":
			return __("Hot and cold operating MPP", "linker-tools");
		case "pv_design_current":
			return __("Design current", "linker-tools");
		case "pv_wiring_protection":
			return __("Wiring and protection", "linker-tools");

		case "grid_output_ceiling":
			return __(
				"Inverter output limit in grid-connected operation",
				"linker-tools",
			);
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
		case "continuous_battery_ac_charge":
			return __("Continuous AC charge power", "linker-tools");
		case "scenario_operating_mode":
			return __("Scenario operating mode", "linker-tools");
		case "scenario_parameter_basis":
			return __("Storage losses and operating conditions", "linker-tools");
		case "scenario_model_domain":
			return __("Converter ports and system topology", "linker-tools");
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
	if (reason === "manufacturer_requirement_matches_operating_context")
		return __(
			"The documented manufacturer requirement applies to the declared operating mode, topology and communication setup. Firmware, model combination and commissioning still require separate checks.",
			"linker-tools",
		);
	if (reason === "parallel_count_uses_applicable_manufacturer_limit")
		return __(
			"Group size is checked only against manufacturer limits documented for the declared operating mode, topology and communication setup. If no applicable limit is documented, it remains unknown.",
			"linker-tools",
		);
	if (reason === "current_cited_controller_network_limit_required")
		return __(
			"The comparison requires a network type and the manufacturer’s inverter limit for that network.",
			"linker-tools",
		);
	if (reason === "controller_network_limit_comparison")
		return __(
			"The limit applies to the selected controller and network. The operating limits of the inverter group are shown separately.",
			"linker-tools",
		);
	if (reason === "maximum_grid_output_is_necessary_bound_only")
		return __(
			"In grid-connected operation, the requested continuous active power from the battery cannot exceed the applicable documented maximum output of the whole inverter. Where the source gives a maximum apparent power S, |P| ≤ S is a necessary upper bound only; S is not an active-power rating. Passing this check does not establish continuous battery output.",
			"linker-tools",
		);
	if (reason === "unit_must_match_plant_connection")
		return __(
			"Each system must match the project grid phases and operating mode.",
			"linker-tools",
		);
	if (reason === "woo_parallel_count_requires_mode_scope")
		return __(
			"The group size is compared with the limit in the product data. Applicability to the declared operating mode and communication setup remains unconfirmed.",
			"linker-tools",
		);
	if (
		reason ===
		"mode_model_firmware_and_battery_association_require_scoped_evidence"
	)
		return __(
			"Joint operation of this group remains unconfirmed for its operating mode, model combination, firmware versions and battery configuration.",
			"linker-tools",
		);
	if (reason === "one_shared_controller_per_declared_group")
		return __(
			"The plan specifies one shared controller for the group. Its model and quantity must match the documented manufacturer requirements.",
			"linker-tools",
		);
	if (reason === "declared_unit_demand_allocation_not_available_plant_output")
		return __(
			"These are declared project requirements allocated to individual systems. Available energy and power at the shared connection remain unconfirmed.",
			"linker-tools",
		);
	if (reason === "joint_delivery_requires_allocation_and_connection_assessment")
		return __(
			"Joint output requires assessment of the individual systems, their allocated requirements and the shared connection.",
			"linker-tools",
		);
	if (reason === "derived_iv_model_with_numerical_readback")
		return __(
			"The fitted parameters reproduce the supplied STC points within the stated numerical tolerance. This is a numerical check, not a manufacturer performance validation.",
			"linker-tools",
		);
	if (reason === "manufacturer_iv_performance_validation_required")
		return __(
			"The fit does not establish model accuracy for this exact module over its operating range. Validation against manufacturer performance data remains required.",
			"linker-tools",
		);
	if (reason === "operating_cell_conditions_required")
		return __(
			"Effective irradiance, hot and cold cell temperatures and their project basis are required for the operating-point calculation.",
			"linker-tools",
		);
	if (reason === "operating_cell_conditions_outside_domain")
		return __(
			"The cold cell temperature must not exceed the hot value, and both must lie within the cited module temperature range.",
			"linker-tools",
		);
	if (reason === "declared_uniform_irradiance_and_cell_conditions")
		return __(
			"The calculation applies the stated effective irradiance uniformly to the modules at each declared cell temperature.",
			"linker-tools",
		);
	if (reason === "modeled_mpp_at_declared_cell_condition")
		return __(
			"This compares the modeled MPP voltage at the declared case with the documented MPPT window. Other irradiance, temperature and shading conditions require their own assessment.",
			"linker-tools",
		);
	if (reason === "modeled_parallel_current_at_declared_conditions")
		return __(
			"Parallel currents are modeled at the declared uniform case. These points do not replace design-current or protection-rating checks.",
			"linker-tools",
		);
	if (reason === "parallel_operating_mpp_requires_matching_strings")
		return __(
			"Different parallel string lengths or orientations do not establish a common operating MPP. The operating-current sum is therefore unresolved.",
			"linker-tools",
		);
	if (reason === "module_operating_curve_not_admissible")
		return __(
			"The model did not produce a finite, physically admissible operating curve for these conditions.",
			"linker-tools",
		);
	if (reason === "module_iv_inputs_missing")
		return __(
			"The model requires STC Voc, Isc, Vmpp and Impp values, plus the Voc and Isc temperature coefficients, from the maintained module record with source references.",
			"linker-tools",
		);
	if (reason === "crystalline_module_basis_missing")
		return __(
			"The cited module record does not establish the crystalline-cell basis required by this model.",
			"linker-tools",
		);
	if (reason === "module_iv_points_inconsistent")
		return __(
			"The supplied STC current or voltage points are inconsistent with a physical single-diode curve.",
			"linker-tools",
		);
	if (reason === "module_iv_fit_not_admissible")
		return __(
			"The fitting result failed its physical or numerical checks. It is not used for operating estimates.",
			"linker-tools",
		);

	if (reason === "physical_input_map_requires_evidence")
		return __(
			"The input number identifies the proposed connection. A cited manufacturer connector map is still required.",
			"linker-tools",
		);
	if (reason === "linear_cold_voc_at_declared_ambient")
		return __(
			"Voc = modules per string × module Voc at STC × [1 + βVoc × (lowest design ambient temperature − 25 °C)]. βVoc is the relative Voc temperature coefficient in 1/°C; divide a value in %/°C by 100. The design temperature and its source are required.",
			"linker-tools",
		);
	if (reason === "stc_operating_point_only")
		return __(
			"This comparison uses STC values: 1,000 W/m² irradiance, 25 °C cell temperature and the AM1.5 reference spectrum.",
			"linker-tools",
		);
	if (reason === "parallel_current_at_stc_only")
		return __(
			"Parallel-string currents are added at STC. Design irradiance, temperature and applicable rating factors require separate checks.",
			"linker-tools",
		);
	if (reason === "hot_and_cold_mpp_model_required")
		return __(
			"Hot and cold operating MPP checks require a suitable module I–V model and documented cell temperatures.",
			"linker-tools",
		);
	if (reason === "design_irradiance_and_rating_rules_required")
		return __(
			"Design currents require documented irradiance, temperature and applicable rating rules.",
			"linker-tools",
		);
	if (reason === "cables_connectors_fuses_and_isolation_require_design")
		return __(
			"Cable routes, conductor ratings, connector compatibility, fuses and isolation still require project-specific design.",
			"linker-tools",
		);

	if (reason === "outage_requires_backup_selection")
		return __(
			"The scenario includes an outage, but the equipment was selected for grid-connected operation.",
			"linker-tools",
		);
	if (reason === "scenario_losses_not_manufacturer_performance")
		return __(
			"The storage losses and efficiencies are scenario inputs. Their applicability to the selected equipment has not been established.",
			"linker-tools",
		);
	if (reason === "selected_port_topology_requires_assessment")
		return __(
			"The scenario uses a single AC bus. Shared converter ports, DC connections and operating limits of the selected system still require assessment.",
			"linker-tools",
		);
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
