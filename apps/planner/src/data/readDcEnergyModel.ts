import { DC_MODEL } from "../domain/dcEnergy.ts";
import { sameJson } from "../domain/draft.ts";
import type { JsonObject } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import {
	energyNumber as number,
	energyRequire as require,
} from "./readEnergyDetails.ts";

/** Check the consumed source-derived port model without running device physics. */
export function verifyDcModel(model: JsonObject, prepared: JsonObject) {
	const losses = readObject(prepared.loss_scenario);
	require(
		model.version === DC_MODEL &&
			model.power_bound_method ===
				"voltage_floor_current_cap_one_selected_port_v1",
	);
	for (const key of [
		"usable_window_kwh",
		"battery",
		"selected_port",
		"pv_input_dc_kw",
		"dc_dc_charge_bus_kw",
		"dc_dc_discharge_bus_kw",
		"connected_bridge",
		"outage_bridge",
	])
		require(sameJson(model[key], prepared[key]));
	for (const key of [
		"eta_bus_to_battery",
		"eta_battery_to_bus",
		"eta_store_charge",
		"eta_store_discharge",
		"internal_aux_kw",
		"standing_loss_rate_per_hour",
	])
		require(model[key] === losses[key]);
	for (const key of ["connected_bridge", "outage_bridge"]) {
		if (model[key] === null) continue;
		const bridge = readObject(model[key]);
		require(
			bridge.eta_forward === losses.eta_inverter_forward &&
				(bridge.reverse_supported !== true ||
					bridge.eta_reverse === losses.eta_inverter_reverse),
		);
	}
	require(
		number(model.charge_terminal_kw) &&
			number(model.discharge_terminal_kw) &&
			readObject(model.selected_port).id === losses.battery_port_id,
	);
}
