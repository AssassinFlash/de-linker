import { readObject } from "../data/readProtocol.ts";
import { documentReference } from "../data/readEquipmentResult.ts";
import Ajv2020 from "ajv/dist/2020.js";
import lossSchema from "../contracts/dc-loss-scenario.schema.json" with { type: "json" };
import parameterSchema from "../contracts/dc-prepared-parameters.schema.json" with { type: "json" };
import { ApiError, type JsonObject } from "../data/protocol.ts";

export const DC_ENERGY_TASK = "shared_dc_energy_replay_v1";
export const DC_MODEL = "constant_window_shared_dc_bus_v1";
export const DC_PV_STAGE =
	"array_mpp_sum_after_declared_dc_factors_before_reference_ac_conversion";

export interface DcLossScenario extends JsonObject {
	readonly schema_version: 1;
	readonly model: typeof DC_MODEL;
	readonly parameter_basis: "explicit_loss_scenario_with_woo_equipment";
	readonly battery_port_id: string;
	readonly battery_temperature_c?: number | null;
	readonly eta_bus_to_battery: number;
	readonly eta_battery_to_bus: number;
	readonly eta_store_charge: number;
	readonly eta_store_discharge: number;
	readonly eta_inverter_forward: number;
	readonly eta_inverter_reverse: number | null;
	readonly internal_aux_kw: number;
	readonly standing_loss_rate_per_hour: number;
	readonly source_note: string;
}

export const DC_LOSS_FIELDS = [
	"eta_bus_to_battery",
	"eta_battery_to_bus",
	"eta_store_charge",
	"eta_store_discharge",
	"eta_inverter_forward",
	"eta_inverter_reverse",
	"internal_aux_kw",
	"standing_loss_rate_per_hour",
] as const;
export type DcLossField = (typeof DC_LOSS_FIELDS)[number];
export interface DcScenarioDraft extends JsonObject {
	readonly source_note: string;
	readonly pv_converter_id: string;
	readonly battery_port_id: string;
	readonly battery_temperature_c?: number | null;
	readonly aux_dc_kw: number | null;
	readonly losses: Readonly<Record<DcLossField, number | null>>;
}
export function emptyDcScenario(): DcScenarioDraft {
	return {
		source_note: "",
		pv_converter_id: "",
		battery_port_id: "",
		battery_temperature_c: null,
		aux_dc_kw: null,
		losses: Object.fromEntries(
			DC_LOSS_FIELDS.map((key) => [key, null]),
		) as DcScenarioDraft["losses"],
	};
}

const ajv = new Ajv2020({ strict: true, strictNumbers: true });
const checkLoss = ajv.compile<DcLossScenario>(lossSchema);
const checkParameters = ajv.compile<JsonObject>(parameterSchema);

export function readDcLossScenario(value: unknown): DcLossScenario {
	if (!checkLoss(value)) throw new ApiError(422, "invalid_dc_loss_scenario");
	return value;
}

export function readDcParameters(value: unknown): JsonObject {
	if (!checkParameters(value)) throw new ApiError(502, "invalid_dc_parameters");
	const revisions = readObject(value.product_revisions);
	for (const [id, raw] of Object.entries(readObject(value.source_facts))) {
		const fact = readObject(raw);
		if (!Object.hasOwn(fact, "value")) continue;

		documentReference(fact.source, true);
		const source = readObject(fact.source);
		const numeric =
			typeof fact.value === "number" &&
			Number.isFinite(fact.value) &&
			fact.value >= 0 &&
			typeof fact.unit === "string";
		const capability =
			source.figure_key === "battery_grid_charging_supported" &&
			typeof fact.value === "string" &&
			(typeof fact.raw_value === "boolean" ||
				["supported", "not_supported", "yes", "no", "true", "false"].includes(
					String(fact.raw_value),
				)) &&
			(fact.unit === null || typeof fact.unit === "string");
		if (!numeric && !capability)
			throw new ApiError(502, "invalid_dc_parameters");

		if (
			typeof source.product_id !== "number" ||
			!Number.isSafeInteger(source.product_id) ||
			source.product_id <= 0 ||
			source.product_revision !== revisions[String(source.product_id)] ||
			id !== `${source.product_id}.${source.figure_key}` ||
			![
				source.document_revision,
				source.blob_sha256,
				source.figure_sha256,
			].every((v) => typeof v === "string" && /^[a-f0-9]{64}$/.test(v))
		)
			throw new ApiError(502, "invalid_dc_parameters");
	}

	return value;
}
