import Ajv2020 from "ajv/dist/2020.js";
import batterySchema from "../contracts/battery-parameters.schema.json" with { type: "json" };
import inputSchema from "../contracts/energy-inputs.schema.json" with { type: "json" };
import dcLossSchema from "../contracts/dc-loss-scenario.schema.json" with { type: "json" };
import { DC_MODEL, DC_LOSS_FIELDS, readDcLossScenario } from "./dcEnergy.ts";
import type { DcLossScenario, DcScenarioDraft } from "./dcEnergy.ts";
import type { JsonObject } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";
import { sameJson } from "./draft.ts";
import type { ProfileSelections } from "./profiles.ts";

export const BATTERY_FIELDS = [
	"usable_window_kwh",
	"charge_ac_kw",
	"discharge_ac_kw",
	"eta_charge",
	"eta_discharge",
	"internal_aux_kw",
	"standing_loss_rate_per_hour",
] as const;
export type BatteryField = (typeof BATTERY_FIELDS)[number];
export interface BatteryParameters extends JsonObject {
	readonly schema_version: 1;
	readonly model: "constant_window_single_ac_bus_v1";
	readonly parameter_basis: "explicit_scenario";
	readonly usable_window_kwh: number;
	readonly charge_ac_kw: number;
	readonly discharge_ac_kw: number;
	readonly eta_charge: number;
	readonly eta_discharge: number;
	readonly internal_aux_kw: number;
	readonly standing_loss_rate_per_hour: number;
}
export interface OperatingPeriod extends JsonObject {
	readonly start_utc: string;
	readonly end_utc: string;
	readonly mode: "connected" | "outage";
	readonly reserve_kwh: number;
	readonly import_cap_kw: number | null;
	readonly export_cap_kw: number | null;
	readonly pv_enabled: boolean;
	readonly allow_grid_charge: boolean;
}
export interface EnergyInputs extends JsonObject {
	readonly coupling?: "independent_ac" | "shared_dc";
	readonly pv_converter_id?: string | null;
	readonly aux_dc_kw?: number | null;
	readonly schema_version: 1;
	readonly gross_load_asset_id: string;
	readonly critical_load_asset_id: string | null;
	readonly pv_available_asset_id: string;
	readonly aux_ac_asset_id: string;
	readonly battery_parameters_asset_id: string;
	readonly initial_inventory: {
		readonly pv_kwh: number;
		readonly grid_kwh: number;
		readonly initial_unknown_kwh: number;
		readonly basis: "user_declared" | "synthetic_fixture";
		readonly source_note: string;
	};
	readonly schedule: readonly OperatingPeriod[];
	readonly controller: "self_consumption_with_reserve_v1";
	readonly terminal_min_kwh: number | null;
}
export interface PeriodDraft extends JsonObject {
	readonly id: string;
	readonly start_utc: string;
	readonly end_utc: string;
	readonly mode: "connected" | "outage" | null;
	readonly reserve_kwh: number | null;
	readonly import_policy: "unlimited" | "limited" | null;
	readonly import_cap_kw: number | null;
	readonly export_policy: "unlimited" | "limited" | null;
	readonly export_cap_kw: number | null;
	readonly pv_enabled: boolean | null;
	readonly allow_grid_charge: boolean | null;
}
export interface ScenarioDraft extends JsonObject {
	readonly schema_version: 1;
	readonly coupling?: "independent_ac" | "shared_dc";
	readonly dc?: DcScenarioDraft;
	readonly battery: Readonly<Record<BatteryField, number | null>>;
	readonly source_note: string;
	readonly initial_inventory: {
		readonly pv_kwh: number | null;
		readonly grid_kwh: number | null;
		readonly initial_unknown_kwh: number | null;
		readonly source_note: string;
	};
	readonly schedule: readonly PeriodDraft[];
	readonly terminal_policy: "none" | "minimum" | null;
	readonly terminal_min_kwh: number | null;
	readonly battery_binding: {
		readonly asset_id: string;
		readonly parameters: BatteryParameters | DcLossScenario;
		readonly source_note: string;
		readonly equipment_selection?: JsonObject;
	} | null;
}

const object = (
	properties: Record<string, object>,
	optional: readonly string[] = [],
): object => ({
	type: "object",
	properties,
	required: Object.keys(properties).filter((key) => !optional.includes(key)),
	additionalProperties: false,
});
const nullable = (value: object): object => ({
	anyOf: [value, { type: "null" }],
});
const choice = (...values: readonly string[]): object =>
	nullable({ enum: values, type: "string" });
const text = { type: "string" };
const nonnegative = batterySchema.properties.usable_window_kwh;
const nullableEnergy = nullable(nonnegative);
const hashId = { type: "string", pattern: "^[a-f0-9]{32}$" };
const ajv = new Ajv2020({
	strict: true,
	strictNumbers: true,
	allErrors: false,
});
const checkBattery = ajv.compile<BatteryParameters>(batterySchema);
const checkInputs = ajv.compile<EnergyInputs>(inputSchema);
const checkParts = ajv.compile<JsonObject>({
	...inputSchema,
	required: inputSchema.required.filter(
		(key) => key !== "battery_parameters_asset_id",
	),
});
const draftShape = object({
	schema_version: { type: "integer", const: 1 },
	coupling: { enum: ["independent_ac", "shared_dc"], type: "string" },
	dc: object(
		{
			source_note: text,
			pv_converter_id: text,
			battery_port_id: text,
			battery_temperature_c: nullable({ type: "number" }),
			aux_dc_kw: nullable({ type: "number" }),
			losses: object(
				Object.fromEntries(
					DC_LOSS_FIELDS.map((key) => [key, nullable({ type: "number" })]),
				),
			),
		},
		["battery_temperature_c"],
	),
	battery: object(
		Object.fromEntries(
			BATTERY_FIELDS.map((key) => [key, nullable({ type: "number" })]),
		),
	),
	source_note: text,
	initial_inventory: object({
		pv_kwh: nullableEnergy,
		grid_kwh: nullableEnergy,
		initial_unknown_kwh: nullableEnergy,
		source_note: text,
	}),
	schedule: {
		type: "array",
		minItems: 1,
		items: object({
			id: hashId,
			start_utc: text,
			end_utc: text,
			mode: choice("connected", "outage"),
			reserve_kwh: nullableEnergy,
			import_policy: choice("unlimited", "limited"),
			import_cap_kw: nullableEnergy,
			export_policy: choice("unlimited", "limited"),
			export_cap_kw: nullableEnergy,
			pv_enabled: nullable({ type: "boolean" }),
			allow_grid_charge: nullable({ type: "boolean" }),
		}),
	},
	terminal_policy: choice("none", "minimum"),
	terminal_min_kwh: nullableEnergy,
	battery_binding: nullable({
		type: "object",
		additionalProperties: false,
		required: ["asset_id", "parameters", "source_note"],
		properties: {
			asset_id: hashId,
			parameters: { anyOf: [batterySchema, dcLossSchema] },
			source_note: text,
			equipment_selection: { type: "object" },
		},
	}),
}) as { required: string[] };
// Optional DC settings preserve every previously saved AC draft verbatim.
draftShape.required = draftShape.required.filter(
	(key) => key !== "coupling" && key !== "dc",
);
const checkDraft = ajv.compile<ScenarioDraft>({
	$defs: { ...batterySchema.$defs, ...dcLossSchema.$defs },
	...draftShape,
});

export function readBatteryParameters(value: unknown): BatteryParameters {
	if (!checkBattery(value))
		throw new ApiError(422, "invalid_battery_parameters");
	return value;
}
export function readEnergyInputs(value: unknown): EnergyInputs {
	if (!checkInputs(value)) throw new ApiError(422, "invalid_energy_inputs");
	return value;
}
export function readScenarioDraft(value: unknown): ScenarioDraft {
	if (!checkDraft(value)) throw new ApiError(422, "invalid_scenario_draft");
	if (
		new Set(value.schedule.map((period) => period.id)).size !==
		value.schedule.length
	)
		throw new ApiError(422, "invalid_scenario_draft");
	return value;
}
export function emptyPeriod(): PeriodDraft {
	return {
		id: crypto.randomUUID().replaceAll("-", ""),
		start_utc: "",
		end_utc: "",
		mode: null,
		reserve_kwh: null,
		import_policy: null,
		import_cap_kw: null,
		export_policy: null,
		export_cap_kw: null,
		pv_enabled: null,
		allow_grid_charge: null,
	};
}
export function emptyScenario(): ScenarioDraft {
	return readScenarioDraft({
		schema_version: 1,
		battery: Object.fromEntries(BATTERY_FIELDS.map((key) => [key, null])),
		source_note: "",
		initial_inventory: {
			pv_kwh: null,
			grid_kwh: null,
			initial_unknown_kwh: null,
			source_note: "",
		},
		schedule: [emptyPeriod()],
		terminal_policy: null,
		terminal_min_kwh: null,
		battery_binding: null,
	});
}
export function scenarioBattery(draft: ScenarioDraft): BatteryParameters {
	if (!draft.source_note.trim())
		throw new ApiError(422, "battery_source_required");
	return readBatteryParameters({
		schema_version: 1,
		model: "constant_window_single_ac_bus_v1",
		parameter_basis: "explicit_scenario",
		...draft.battery,
	});
}

export function scenarioParts(
	draft: ScenarioDraft,
	profiles: ProfileSelections,
	equipmentSelection: JsonObject | null = null,
): {
	readonly parameters: BatteryParameters | DcLossScenario;
	readonly inputs: JsonObject;
} {
	const dc = draft.coupling === "shared_dc";
	if (dc && !draft.dc?.source_note.trim())
		throw new ApiError(422, "battery_source_required");
	if (dc && !equipmentSelection)
		throw new ApiError(422, "dc_equipment_required");
	if (dc && (!draft.dc?.pv_converter_id.trim() || draft.dc.aux_dc_kw === null))
		throw new ApiError(422, "dc_connection_required");
	const parameters = dc
		? readDcLossScenario({
				schema_version: 1,
				model: DC_MODEL,
				parameter_basis: "explicit_loss_scenario_with_woo_equipment",
				...draft.dc?.losses,
				battery_port_id: draft.dc?.battery_port_id,
				...(draft.dc!.battery_temperature_c === undefined
					? {}
					: { battery_temperature_c: draft.dc!.battery_temperature_c }),
				source_note: draft.dc!.source_note,
			})
		: scenarioBattery(draft);
	const { gross_load, critical_load, pv_available_ac, aux_ac } =
		profiles.selected;
	if (!gross_load || !pv_available_ac || !aux_ac)
		throw new ApiError(422, "scenario_profiles_required");
	const inventory = compileInitialInventory(draft.initial_inventory);
	const total =
		(inventory.pv_kwh ?? 0) +
		(inventory.grid_kwh ?? 0) +
		(inventory.initial_unknown_kwh ?? 0);
	if (parameters.model !== DC_MODEL && total > parameters.usable_window_kwh)
		throw new ApiError(422, "initial_inventory_exceeds_window");
	const terminal = compileTerminalMinimum(draft);
	const schedule = compileOperatingPeriods(draft.schedule, critical_load);
	const inputs: JsonObject = {
		schema_version: 1,
		...(dc
			? {
					coupling: "shared_dc",
					pv_converter_id: draft.dc!.pv_converter_id,
					aux_dc_kw: draft.dc!.aux_dc_kw,
				}
			: {}),
		gross_load_asset_id: gross_load,
		critical_load_asset_id: critical_load ?? null,
		pv_available_asset_id: pv_available_ac,
		aux_ac_asset_id: aux_ac,
		initial_inventory: { ...inventory, basis: "user_declared" },
		schedule,
		controller: "self_consumption_with_reserve_v1",
		terminal_min_kwh: terminal,
	};
	if (!checkParts(inputs)) throw new ApiError(422, "invalid_energy_inputs");
	return { parameters, inputs };
}

export function compileScenario(
	draft: ScenarioDraft,
	profiles: ProfileSelections,
	equipmentSelection: JsonObject | null = null,
): EnergyInputs {
	const { parameters, inputs } = scenarioParts(
			draft,
			profiles,
			equipmentSelection,
		),
		binding = draft.battery_binding;
	if (
		!binding ||
		!sameJson(binding.parameters, parameters) ||
		binding.source_note !==
			(draft.coupling === "shared_dc"
				? draft.dc!.source_note
				: draft.source_note) ||
		(draft.coupling === "shared_dc" &&
			!sameJson(binding.equipment_selection, equipmentSelection))
	)
		throw new ApiError(422, "battery_not_prepared");
	return readEnergyInputs({
		...inputs,
		battery_parameters_asset_id: binding.asset_id,
	});
}

/** Transport shape only. The pinned server time axis validates actual instants,
 * ordering, continuity and source coverage; browser Date rounding is not used. */
function explicitInstant(value: string): boolean {
	return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})$/.test(
		value,
	);
}

export function scenarioInputs(
	inputs: JsonObject,
	scenario: ScenarioDraft,
): JsonObject {
	// The effective replay input is invalidated on editing. Undo restores the prior
	// replay together with its setup; a job/result itself remains immutable.
	return {
		...invalidateEnergyReplay(inputs),
		energy_scenario: readObject(readScenarioDraft(scenario)),
	};
}

export function invalidateEnergyReplay(inputs: JsonObject): JsonObject {
	const { energy_replay: _old, energy_plant: _joint, ...rest } = inputs;
	return rest;
}

export function compileOperatingPeriods(
	periods: readonly PeriodDraft[],
	critical_load: string | undefined,
): OperatingPeriod[] {
	return periods.map((period) => {
		if (
			!period.mode ||
			period.reserve_kwh === null ||
			period.pv_enabled === null ||
			(period.mode === "connected" &&
				(period.allow_grid_charge === null ||
					!period.import_policy ||
					!period.export_policy)) ||
			(period.mode === "outage" && !critical_load)
		)
			throw new ApiError(422, "operating_period_incomplete");
		if (period.mode === "outage" && period.allow_grid_charge === true)
			throw new ApiError(422, "outage_grid_charge");
		if (!explicitInstant(period.start_utc) || !explicitInstant(period.end_utc))
			throw new ApiError(422, "period_offset_required");
		for (const [policy, cap] of [
			[period.import_policy, period.import_cap_kw],
			[period.export_policy, period.export_cap_kw],
		] as const)
			if (period.mode === "connected" && policy === "limited" && cap === null)
				throw new ApiError(422, "grid_cap_required");
		return {
			start_utc: period.start_utc,
			end_utc: period.end_utc,
			mode: period.mode,
			reserve_kwh: period.reserve_kwh,
			import_cap_kw:
				period.mode === "outage"
					? 0
					: period.import_policy === "unlimited"
						? null
						: period.import_cap_kw,
			export_cap_kw:
				period.mode === "outage"
					? 0
					: period.export_policy === "unlimited"
						? null
						: period.export_cap_kw,
			pv_enabled: period.pv_enabled,
			allow_grid_charge:
				period.mode === "outage" ? false : period.allow_grid_charge!,
		};
	});
}

export function compileInitialInventory(
	inventory: ScenarioDraft["initial_inventory"],
): EnergyInputs["initial_inventory"] {
	if (
		!inventory.source_note.trim() ||
		Object.entries(inventory).some(
			([key, value]) => key !== "source_note" && value === null,
		)
	)
		throw new ApiError(422, "initial_inventory_required");
	return {
		...inventory,
		pv_kwh: inventory.pv_kwh!,
		grid_kwh: inventory.grid_kwh!,
		initial_unknown_kwh: inventory.initial_unknown_kwh!,
		basis: "user_declared",
	};
}

export function compileTerminalMinimum(
	draft: Pick<ScenarioDraft, "terminal_policy" | "terminal_min_kwh">,
): number | null {
	if (
		!draft.terminal_policy ||
		(draft.terminal_policy === "minimum" && draft.terminal_min_kwh === null)
	)
		throw new ApiError(422, "terminal_condition_required");
	return draft.terminal_policy === "none" ? null : draft.terminal_min_kwh;
}
