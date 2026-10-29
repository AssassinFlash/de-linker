import { ApiError } from "../../data/protocol.ts";
import { __ } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { GeometryInputError } from "../../domain/validateGeometry.ts";

export function energyConstraintText(constraintId: unknown): string | null {
	switch (constraintId) {
		case "plant_dc_duplicate_pv_source":
			return __(
				"The same roof PV source cannot also be counted as an additional AC source.",
				"linker-tools",
			);
		case "plant_dc_pv_nameplate_mismatch":
			return __(
				"Each converter’s allocated DC PV nameplate rating must match the STC rating of its assigned roof PV group.",
				"linker-tools",
			);
		case "joint_outage_dc_topology":
			return __(
				"Multi-converter backup requires a documented island-mode topology. This calculation does not provide that evidence.",
				"linker-tools",
			);
		case "plant_ac_reverse_capability":
		case "explicit_reverse_capability":
			return __(
				"AC charging capability and power limit are not established for this converter. Review the selected product and its source documents before preparing the joint calculation.",
				"linker-tools",
			);
		case "joint_outage_ac_pv_topology":
			return __(
				"AC PV during an outage requires separately established island-operation topology. If support is unconfirmed, mark PV as unavailable for the outage periods and review the backup connections.",
				"linker-tools",
			);
		case "battery_operating_temperature_required":
			return __(
				"The selected battery needs a declared operating temperature for this scenario.",
				"linker-tools",
			);
		case "battery_temperature_outside_condition":
			return __(
				"The declared battery temperature is outside a documented operating range. Review the scenario temperature and source details.",
				"linker-tools",
			);
		case "module_count_outside_condition":
		case "module_count_column_required":
			return __(
				"A documented configuration could not be matched to the selected module count. Review the equipment selection and source details.",
				"linker-tools",
			);
		case "column_value_unit_mismatch":
			return __(
				"Values or units in the selected product table could not be matched consistently. This calculation could not be prepared.",
				"linker-tools",
			);
		case "uninterpreted_condition":
		case "capacity_reference_conditions":
			return __(
				"A documented condition could not be checked for this scenario. Review the source details.",
				"linker-tools",
			);
	}
	return null;
}

export function energyErrorText(error: unknown): string {
	const specific =
		error instanceof ApiError
			? energyConstraintText(error.evidenceIssue?.constraint_id)
			: null;
	if (specific) return specific;
	const code =
		error instanceof ApiError || error instanceof GeometryInputError
			? error.code
			: "";
	switch (code) {
		case "geometric_pv_inputs_invalid":
			return __(
				"The PV reference needs a retained weather source, two ordered sampling grids and complete PV model parameters.",
				"linker-tools",
			);
		case "invalid_geometric_pv_limits":
			return __(
				"The calculation service did not provide valid limits for this PV method. Saved inputs remain available.",
				"linker-tools",
			);
		case "plant_dc_assignment_required":
			return __(
				"Select the PV group and AC charging option, and enter the DC auxiliary demand for each converter.",
				"linker-tools",
			);
		case "plant_dc_duplicate_pv_source":
			return __(
				"The same roof PV source cannot also be counted as an additional AC source.",
				"linker-tools",
			);
		case "plant_energy_dc_pv_used":
			return __(
				"This calculation includes PV only through a separate AC generation input. In the storage plan, set the total DC PV nameplate rating and each converter's DC PV allocation to zero. Confirm that every storage converter's DC PV inputs are unused.",
				"linker-tools",
			);
		case "invalid_plant_energy_inputs":
			return __(
				"Review the equipment plan, each unit's storage settings and the shared operating periods before preparing this calculation.",
				"linker-tools",
			);
		case "equipment_plant_single_candidate":
			return __(
				"This search covers a single system. Choose products within each system when editing a multi-system plan.",
				"linker-tools",
			);
		case "equipment_plant_incomplete":
		case "equipment_plant_requires_preparation":
			return __(
				"Complete the project requirements and equipment for each system, then prepare and save the multi-system plan.",
				"linker-tools",
			);
		case "dc_equipment_required":
			return __(
				"Select and prepare an inverter and battery before preparing the shared-inverter calculation.",
				"linker-tools",
			);
		case "dc_connection_required":
			return __(
				"The shared-inverter calculation needs a PV conversion group, a connected battery port and an explicit DC auxiliary demand.",
				"linker-tools",
			);
		case "dc_save_required":
			return __(
				"Save the project before preparing DC parameters so that the calculation uses the saved equipment selection.",
				"linker-tools",
			);
		case "invalid_dc_loss_scenario":
			return __(
				"Loss assumptions need attention. Efficiencies must be greater than 0% and no more than 100%; auxiliary power and standing-loss rate must be zero or greater. A source or assumption note is required.",
				"linker-tools",
			);
		case "evidence_missing":
			return __(
				"Required source information is missing for this calculation. Review the selected equipment, PV source and loss assumptions.",
				"linker-tools",
			);
		case "method_domain_exceeded":
			return __(
				"This connection or operating mode is outside the selected calculation model. Review the system connection and operating periods.",
				"linker-tools",
			);
		case "report_logo_invalid":
			return __(
				"The logo could not be used. Choose a PNG or JPG of up to 500 kB.",
				"linker-tools",
			);
		case "report_inputs_changed":
			return __(
				"A selected result does not match the saved project inputs. Choose a matching result.",
				"linker-tools",
			);
		case "incomplete_module_reference":
		case "invalid_source_url":
			return __(
				"The coefficient document reference needs an HTTP or HTTPS URL without login credentials, a SHA-256 checksum with 64 characters (0-9 and a-f) and a page number that is a whole number greater than zero.",
				"linker-tools",
			);
		case "pv_parameters_incomplete":
			return __(
				"The PV model needs complete module, array and conversion parameters with source notes. Percentage factors must be between 0% and 100%; conversion efficiencies must be greater than 0% and no more than 100%, and DC reference power must be greater than zero.",
				"linker-tools",
			);
		case "pv_layout_changed":
			return __(
				"PV parameters must match the active roof layout. Each array needs one parameter set and exactly one conversion group; each module specification needs its temperature coefficient.",
				"linker-tools",
			);
		case "pv_location_required":
			return __(
				"PV generation needs roof coordinates and a declared north reference. These can be set in Roof design.",
				"linker-tools",
			);
		case "pv_weather_required":
			return __(
				"PV generation needs a selected weather source. A completed weather result can be selected in Saved calculations.",
				"linker-tools",
			);
		case "pv_weather_location_mismatch":
			return __(
				"The weather coordinates differ from the roof reference point. This model requires weather and roof coordinates to match.",
				"linker-tools",
			);
		case "weather_parameters_incomplete":
			return __(
				"Weather settings need valid coordinates, whole source and calculation years, a radiation database and a terrain-horizon choice.",
				"linker-tools",
			);
		case "weather_year_order":
			return __(
				"The last source year must be the same as or later than the first source year.",
				"linker-tools",
			);
		case "weather_leap_axis":
			return __(
				"The calculation year must be a non-leap year. This model uses 8,760 hourly intervals.",
				"linker-tools",
			);
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
		case "product_evidence_changed":
			return __(
				"A new check requires current product data. Reload the data and prepare the selection again.",
				"linker-tools",
			);
		case "equipment_requirements_incomplete":
			return __("Enter the search requirements first.", "linker-tools");
		case "equipment_condition_binding_changed":
		case "equipment_condition_revision_changed":
			return __(
				"Some device entries refer to a different selection or product revision. The original entries are kept in Device model and firmware. Remove them and enter the details for the current devices before saving.",
				"linker-tools",
			);
		case "equipment_condition_requires_preparation":
			return __(
				"The device entries are saved, but the equipment selection needs preparation before a new check or report. Prepare the selection and save the project.",
				"linker-tools",
			);
		case "pv_string_plan_incomplete":
		case "equipment_selection_incomplete":
			return __(
				"Equipment selection requires a product and valid quantities.",
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
	const issue = error instanceof ApiError ? error.evidenceIssue : null;
	return error ? (
		<Notice error>
			<p>{energyErrorText(error)}</p>
			{issue && (
				<details>
					<summary>{__("Source details", "linker-tools")}</summary>
					<dl className="lp-field-summary">
						{Object.entries(issue).map(([key, value]) => (
							<div key={key}>
								<dt>
									{key === "product_id"
										? __("Product", "linker-tools")
										: key === "fact_id"
											? __("Source field", "linker-tools")
											: __("Constraint", "linker-tools")}
								</dt>
								<dd>{String(value)}</dd>
							</div>
						))}
					</dl>
				</details>
			)}
		</Notice>
	) : null;
}
