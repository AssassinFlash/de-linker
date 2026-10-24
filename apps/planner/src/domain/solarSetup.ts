import Ajv2020 from "ajv/dist/2020.js";
import weatherSchema from "../contracts/weather-acquisition.schema.json" with { type: "json" };
import pvSchema from "../contracts/pv-generation.schema.json" with { type: "json" };
import geometryPolicy from "../contracts/geometry-policy.json" with { type: "json" };
import type { JsonObject, Json } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";
import { readGeometry } from "./validateGeometry.ts";
import type { GeometryDocument } from "./geometry.ts";
import { sameJson } from "./draft.ts";
import { invalidateEnergyReplay } from "./energyScenario.ts";

export interface WeatherDraft extends JsonObject {
	readonly schema_version: 1;
	readonly request: {
		readonly schema_version: 1;
		readonly api_version: "5.3";
		readonly latitude_deg: number | null;
		readonly longitude_deg: number | null;
		readonly start_year: number | null;
		readonly end_year: number | null;
		readonly use_terrain_horizon: boolean | null;
		readonly radiation_database_policy: "provider_default_with_verified_echo";
		readonly expected_radiation_database: "PVGIS-SARAH3" | "PVGIS-ERA5" | null;
		readonly expected_meteo_database: "ERA5";
	};
	readonly interpretation: {
		readonly schema_version: 1;
		readonly synthetic_energy_year: number | null;
		readonly solar_date_policy: "original_selected_year_plus_reported_irradiance_offset";
		readonly output_axis_policy: "nonleap_synthetic_utc_hourly_scenario_v1";
		readonly power_reconstruction: "representative_pv_output_over_declared_intervals_v1";
	};
}
export interface ModuleDraft extends JsonObject {
	readonly module_spec_id: string;
	readonly gamma_pdc_per_c: number | null;
	readonly source: {
		readonly kind: "user_declared" | "datasheet" | null;
		readonly note: string;
		readonly document_sha256: string | null;
		readonly url: string | null;
		readonly page: number | null;
	};
}
export const ARRAY_FACTORS = [
	"albedo",
	"beam_iam_b",
	"sky_diffuse_iam_factor",
	"ground_diffuse_iam_factor",
	"spectral_factor",
	"soiling_factor",
	"dc_wiring_factor",
	"dc_mismatch_factor",
] as const;
export type ArrayFactor = (typeof ARRAY_FACTORS)[number];
export interface ArrayDraft extends JsonObject {
	readonly array_id: string;
	readonly transposition:
		"isotropic" | "haydavies" | "perez" | "perez-driesse" | null;
	readonly albedo: number | null;
	readonly beam_iam_model: "ashrae";
	readonly beam_iam_b: number | null;
	readonly sky_diffuse_iam_factor: number | null;
	readonly ground_diffuse_iam_factor: number | null;
	readonly spectral_factor: number | null;
	readonly soiling_factor: number | null;
	readonly dc_wiring_factor: number | null;
	readonly dc_mismatch_factor: number | null;
	readonly thermal: {
		readonly model: "sapm_cell";
		readonly a: number | null;
		readonly b: number | null;
		readonly delta_t_c: number | null;
		readonly source_note: string;
	};
	readonly source_note: string;
}
export interface ConverterDraft extends JsonObject {
	readonly id: string;
	readonly array_ids: readonly string[];
	readonly model: "pvwatts";
	readonly input_assumption: "independent_mppt_array_mpp_sum";
	readonly reference_dc_power_w: number | null;
	readonly eta_nominal: number | null;
	readonly eta_reference: number | null;
	readonly source_note: string;
}
export interface PvDraft extends JsonObject {
	readonly schema_version: 1;
	readonly model: "uniform_unshaded_pvlib_reference_v1";
	readonly pvlib_version: "0.16.1";
	readonly temporal_policy: "representative_pv_output_over_declared_intervals_v1";
	readonly shading_policy: "explicit_unshaded_reference";
	readonly modules: readonly ModuleDraft[];
	readonly arrays: readonly ArrayDraft[];
	readonly converters: readonly ConverterDraft[];
	readonly source_note: string;
}
export interface SolarSetup extends JsonObject {
	readonly schema_version: 1;
	readonly weather: WeatherDraft;
	readonly pv: PvDraft;
}

const ajv = new Ajv2020({ strict: true, strictNumbers: true });
const checkWeather = ajv.compile<JsonObject>(weatherSchema),
	checkPv = ajv.compile<JsonObject>(pvSchema);
/** Drafts retain incomplete numeric/choice leaves; constants and structure stay versioned.
 * Every prepared document still passes the untouched exported service schema. */
function draftSchema(value: unknown, field = ""): object {
	const node = value as Record<string, unknown>;
	if (field === "SchemaVersion" || field === "Identifier") return node;
	if (node.const !== undefined) return node;
	if (node.$defs)
		return {
			...node,
			$defs: Object.fromEntries(
				Object.entries(node.$defs as object).map(([key, item]) => [
					key,
					draftSchema(item, key),
				]),
			),
			properties: Object.fromEntries(
				Object.entries(node.properties as object).map(([key, item]) => [
					key,
					draftSchema(item, key),
				]),
			),
		};
	if (node.properties)
		return {
			...node,
			properties: Object.fromEntries(
				Object.entries(node.properties as object).map(([key, item]) => [
					key,
					draftSchema(item, key),
				]),
			),
		};
	if (node.$ref) return node;
	if (node.items)
		return { ...node, minItems: 0, items: draftSchema(node.items, field) };
	if (node.anyOf)
		return {
			...node,
			anyOf: (node.anyOf as unknown[]).map((item) => draftSchema(item, field)),
		};
	if (node.type === "null") return node;
	if (["id", "array_id", "module_spec_id", "array_ids"].includes(field))
		return node;
	if (node.type === "number" || node.type === "integer")
		return { anyOf: [{ type: "number" }, { type: "null" }] };
	if (node.type === "boolean" || node.enum)
		return { anyOf: [node, { type: "null" }] };
	if (node.type === "string")
		return {
			type: "string",
			...(node.maxLength === undefined ? {} : { maxLength: node.maxLength }),
		};
	return node;
}
const checkWeatherDraft = ajv.compile<WeatherDraft>(draftSchema(weatherSchema));
const checkPvDraft = ajv.compile<PvDraft>(draftSchema(pvSchema));
export function emptyWeather(): WeatherDraft {
	return {
		schema_version: 1,
		request: {
			schema_version: 1,
			api_version: "5.3",
			latitude_deg: null,
			longitude_deg: null,
			start_year: null,
			end_year: null,
			use_terrain_horizon: null,
			radiation_database_policy: "provider_default_with_verified_echo",
			expected_radiation_database: null,
			expected_meteo_database: "ERA5",
		},
		interpretation: {
			schema_version: 1,
			synthetic_energy_year: null,
			solar_date_policy:
				"original_selected_year_plus_reported_irradiance_offset",
			output_axis_policy: "nonleap_synthetic_utc_hourly_scenario_v1",
			power_reconstruction:
				"representative_pv_output_over_declared_intervals_v1",
		},
	};
}
export function emptyPv(): PvDraft {
	return {
		schema_version: 1,
		model: "uniform_unshaded_pvlib_reference_v1",
		pvlib_version: "0.16.1",
		temporal_policy: "representative_pv_output_over_declared_intervals_v1",
		shading_policy: "explicit_unshaded_reference",
		modules: [],
		arrays: [],
		converters: [],
		source_note: "",
	};
}
export function emptyConverter(): ConverterDraft {
	return {
		id: "converter_" + crypto.randomUUID().replaceAll("-", ""),
		array_ids: [],
		model: "pvwatts",
		input_assumption: "independent_mppt_array_mpp_sum",
		reference_dc_power_w: null,
		eta_nominal: null,
		eta_reference: null,
		source_note: "",
	};
}
export function readSolarSetup(inputs: JsonObject): SolarSetup {
	const saved = inputs.solar_setup;
	const row =
		saved === undefined
			? {
					schema_version: 1,
					weather: inputs.weather_acquisition ?? emptyWeather(),
					pv: inputs.pv_generation ?? emptyPv(),
				}
			: readObject(saved);
	if (
		row.schema_version !== 1 ||
		Object.keys(row).sort().join() !== "pv,schema_version,weather" ||
		!checkWeatherDraft(row.weather) ||
		!checkPvDraft(row.pv)
	)
		throw new ApiError(422, "unsupported_solar_setup");
	return row as SolarSetup;
}
export function solarInputs(inputs: JsonObject, next: SolarSetup): JsonObject {
	readSolarSetup({ solar_setup: next });
	const previous = readSolarSetup(inputs),
		copy: Record<string, Json> = { ...inputs, solar_setup: next };
	if (!sameJson(previous.weather, next.weather))
		delete copy.weather_acquisition;
	if (!sameJson(previous.pv, next.pv)) {
		delete copy.pv_generation;
		return invalidateEnergyReplay(copy);
	}
	return copy;
}
export function compileWeather(value: WeatherDraft): JsonObject {
	if (!checkWeather(value))
		throw new ApiError(422, "weather_parameters_incomplete");
	const start = value.request.start_year!,
		end = value.request.end_year!,
		year = value.interpretation.synthetic_energy_year!;
	if (end < start) throw new ApiError(422, "weather_year_order");
	if (year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0))
		throw new ApiError(422, "weather_leap_axis");
	return value;
}
export function activePvGeometry(value: Json | undefined): {
	geometry: GeometryDocument;
	arrays: GeometryDocument["arrays"];
} {
	const geometry = readGeometry(value, geometryPolicy);
	return {
		geometry,
		arrays: geometry.arrays.filter(
			(array) =>
				array.rows * array.columns > new Set(array.excluded_slots).size,
		),
	};
}
export function alignPv(
	value: PvDraft,
	geometryValue: Json | undefined,
): PvDraft {
	const { arrays } = activePvGeometry(geometryValue),
		modules = [...new Set(arrays.map((array) => array.module_spec_id))];
	return {
		...value,
		modules: modules.map(
			(id) =>
				value.modules.find((item) => item.module_spec_id === id) ?? {
					module_spec_id: id,
					gamma_pdc_per_c: null,
					source: {
						kind: "user_declared",
						note: "",
						url: null,
						document_sha256: null,
						page: null,
					},
				},
		),
		arrays: arrays.map(
			(array) =>
				value.arrays.find((item) => item.array_id === array.id) ?? {
					array_id: array.id,
					transposition: null,
					albedo: null,
					beam_iam_model: "ashrae",
					beam_iam_b: null,
					sky_diffuse_iam_factor: null,
					ground_diffuse_iam_factor: null,
					spectral_factor: null,
					soiling_factor: null,
					dc_wiring_factor: null,
					dc_mismatch_factor: null,
					thermal: {
						model: "sapm_cell",
						a: null,
						b: null,
						delta_t_c: null,
						source_note: "",
					},
					source_note: "",
				},
		),
		converters: value.converters.map((group) => ({
			...group,
			array_ids: group.array_ids.filter((id) =>
				arrays.some((array) => array.id === id),
			),
		})),
	};
}
export function compilePv(
	value: PvDraft,
	geometryValue: Json | undefined,
): JsonObject {
	if (!checkPv(value)) throw new ApiError(422, "pv_parameters_incomplete");
	const { geometry, arrays } = activePvGeometry(geometryValue);
	const sameSet = (actual: readonly string[], expected: readonly string[]) =>
		actual.length === new Set(actual).size &&
		actual.length === new Set(expected).size &&
		actual.every((id) => expected.includes(id));
	if (
		!arrays.length ||
		!sameSet(
			value.arrays.map((a) => a.array_id),
			arrays.map((a) => a.id),
		) ||
		!sameSet(
			value.modules.map((m) => m.module_spec_id),
			arrays.map((a) => a.module_spec_id),
		) ||
		!sameSet(
			value.converters.flatMap((group) => group.array_ids),
			arrays.map((a) => a.id),
		) ||
		new Set(value.converters.map((group) => group.id)).size !==
			value.converters.length
	)
		throw new ApiError(422, "pv_layout_changed");
	if (
		!geometry.coordinate_system.anchor ||
		geometry.coordinate_system.north_reference === "unreferenced"
	)
		throw new ApiError(422, "pv_location_required");
	// Apply the same complete source-reference checks as geometry module evidence.
	readGeometry(
		{
			...geometry,
			module_specs: geometry.module_specs.map((module) => {
				const parameters = value.modules.find(
					(p) => p.module_spec_id === module.id,
				);
				return parameters ? { ...module, source: parameters.source } : module;
			}),
		},
		geometryPolicy,
	);
	return value;
}
export function prepareWeatherInputs(inputs: JsonObject): JsonObject {
	const setup = readSolarSetup(inputs),
		weather = compileWeather(setup.weather);
	const next: Record<string, Json> = {
		...inputs,
		solar_setup: setup,
		weather_acquisition: weather,
	};
	if (!sameJson(inputs.weather_acquisition, weather)) {
		// Save must not bind a replacement request to the previous owned weather.
		// Immutable sources/results stay in history; adoption is still explicit.
		delete next.pv_preparation;
		return invalidateEnergyReplay(next);
	}
	return next;
}
export function preparePvInputs(inputs: JsonObject): JsonObject {
	const setup = readSolarSetup(inputs);
	return {
		...inputs,
		solar_setup: setup,
		pv_generation: compilePv(setup.pv, inputs.geometry),
	};
}
