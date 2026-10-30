import { ApiError, type JsonObject } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import { sameJson } from "../domain/draft.ts";
import { isPlantEnergyTask } from "../domain/plantEnergy.ts";
export const energyHash = (value: unknown): value is string =>
	typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
export const energyNumber = (value: unknown): value is number =>
	typeof value === "number" && Number.isFinite(value) && value >= 0;
export function energyRequire(condition: unknown): asserts condition {
	if (!condition) throw new ApiError(502, "invalid_run_result");
}
const positive = (v: unknown): v is number => energyNumber(v) && v > 0;
const utc = (v: unknown): v is string =>
	typeof v === "string" &&
	/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)$/.test(v);
import { DC_PV_STAGE } from "../domain/dcEnergy.ts";
import { GEOMETRIC_PV_RESULTS } from "../domain/geometricPv.ts";
export function verifyEnergyDetails(
	result: JsonObject,
	pinned: JsonObject,
	dc: boolean | "plant_dc",
) {
	const mixed = dc === "plant_dc";
	dc = dc === true;
	energyRequire(
		typeof result.interval_count === "number" &&
			Number.isSafeInteger(result.interval_count) &&
			result.interval_count > 0,
	);
	for (const assessment of [
		result.equipment_release,
		result.country_assessment,
	])
		if (readObject(assessment).status !== "not_assessed")
			throw new ApiError(502, "unsupported_run_assessment");
	const metrics = readObject(result.metrics);
	if (mixed)
		for (const name of [
			"pv_generated_dc_kwh",
			"pv_curtailed_dc_kwh",
			"independent_pv_curtailed_ac_kwh",
		])
			energyRequire(energyNumber(metrics[name]));
	for (const name of [
		"load_demand_kwh",
		"solar_load_kwh",
		"grid_import_kwh",
		dc ? "pv_generated_dc_kwh" : "pv_generated_ac_kwh",
		"unserved_load_kwh",
	])
		energyRequire(energyNumber(metrics[name]));
	energyRequire(
		["gross_load", "critical_load", "mixed"].includes(
			String(metrics.load_measurement_scope),
		),
	);
	for (const name of ["solar_autarky", "pv_input_self_use"]) {
		const ratio = readObject(metrics[name]);
		energyRequire(
			ratio.value === null
				? typeof ratio.undefined_reason === "string" &&
						ratio.undefined_reason.length > 0
				: typeof ratio.value === "number" &&
						Number.isFinite(ratio.value) &&
						ratio.undefined_reason === null,
		);
	}
	const autarky = readObject(metrics.solar_autarky),
		pvUse = readObject(metrics.pv_input_self_use),
		generation = metrics[dc ? "pv_generated_dc_kwh" : "pv_generated_ac_kwh"];
	const autarkyReason =
		metrics.load_measurement_scope !== "gross_load"
			? isPlantEnergyTask(result.kind)
				? "critical_or_mixed_demand_is_not_whole_site_load"
				: "requested_load_scope_is_not_whole_site_gross"
			: metrics.load_demand_kwh === 0
				? "gross_load_is_zero"
				: null;
	energyRequire(
		autarky.undefined_reason === autarkyReason &&
			(autarky.value === null) === (autarkyReason !== null),
	);
	energyRequire(
		pvUse.undefined_reason ===
			(mixed
				? "mixed_pv_measurement_stages"
				: generation === 0
					? "pv_generation_is_zero"
					: null) && (pvUse.value === null) === (mixed || generation === 0),
	);
	const verification = readObject(result.verification),
		checks = verification.checks;
	energyRequire(
		typeof verification.passed === "boolean" &&
			["satisfied", "violated"].includes(
				String(result.scenario_constraint_status),
			) &&
			verification.passed ===
				(result.scenario_constraint_status === "satisfied") &&
			Array.isArray(checks) &&
			checks.length > 0,
	);
	for (const raw of checks as readonly unknown[]) {
		const check = readObject(raw);
		energyRequire(
			typeof check.code === "string" &&
				check.code.length > 0 &&
				typeof check.passed === "boolean" &&
				energyNumber(check.worst_violation) &&
				energyNumber(check.allowance) &&
				energyNumber(check.arithmetic_allowance) &&
				["kW", "kWh"].includes(String(check.unit)) &&
				typeof check.at_interval === "number" &&
				Number.isSafeInteger(check.at_interval) &&
				check.at_interval >= 0 &&
				check.at_interval < result.interval_count,
		);
	}
	energyRequire(
		verification.passed ===
			(checks as readonly JsonObject[]).every((check) => check.passed === true),
	);
	const periods = readObject(result.profile_interpretation).operating_periods;
	energyRequire(Array.isArray(periods) && periods.length > 0);
	for (const raw of periods as readonly unknown[]) {
		const period = readObject(raw),
			profiles = readObject(period.profiles);
		energyRequire(
			utc(period.start_utc) &&
				utc(period.end_utc) &&
				["connected", "outage"].includes(String(period.mode)),
		);
		const unitModels = mixed
			? (readObject(result.model).units as readonly JsonObject[])
			: [];
		const expected = mixed
			? [
					period.mode === "outage" ? "critical_load" : "gross_load",
					"aux_ac",
					...(pinned["pv_available_ac.raw"] === undefined
						? []
						: ["pv_available_ac"]),
					...((
						readObject(result.model).ac_pv_converter_ids as readonly unknown[]
					).length
						? ["reference_ac"]
						: []),
					...unitModels
						.filter((u) => u.pv_converter_id !== null)
						.map((u) => `unit:${u.unit_id}:pv_available_dc`),
				]
			: period.mode === "outage"
				? [
						"critical_load",
						dc ? "pv_available_dc" : "pv_available_ac",
						"aux_ac",
					]
				: ["gross_load", dc ? "pv_available_dc" : "pv_available_ac", "aux_ac"];
		energyRequire(
			Object.keys(profiles).sort().join() === expected.sort().join(),
		);
		for (const [role, rawProfile] of Object.entries(profiles)) {
			const unit = mixed
				? unitModels.find((u) => role === `unit:${u.unit_id}:pv_available_dc`)
				: undefined;
			const reference = !!unit || (mixed && role === "reference_ac");
			const measured = unit
				? "pv_available_dc"
				: mixed && role === "reference_ac"
					? "pv_available_ac"
					: role;
			const key = reference ? "pv_reference" : role;
			const profile = readObject(rawProfile),
				source = readObject(profile.source),
				modelInput = pinned[key + ".pv_model_inputs"];
			// A generated roof profile identifies its frozen model input
			// bundle as the series source. The asset's raw bytes remain the
			// original weather; CSV/system-output profiles identify raw bytes.
			let sourceMatches = source.raw_sha256 === pinned[key + ".raw"];
			const geometricInput = pinned[key + ".model.inputs"];
			if (geometricInput !== undefined) {
				const details = readObject(source.details);
				sourceMatches =
					!reference &&
					!dc &&
					role === "pv_available_ac" &&
					source.origin === "modelled" &&
					GEOMETRIC_PV_RESULTS.some(
						(item) =>
							details.model === item.model && details.model_role === item.role,
					) &&
					details.output_boundary ===
						"scenario_ac_potential_before_site_export_and_storage_control" &&
					energyHash(geometricInput) &&
					energyHash(pinned[key + ".model.witness"]) &&
					energyHash(pinned[key + ".weather.raw"]) &&
					energyHash(pinned[key + ".weather.metadata"]) &&
					energyHash(pinned[key + ".project.parameters"]) &&
					energyHash(pinned[key + ".woo.module_inputs"]) &&
					energyHash(details.geometry_sha256) &&
					energyHash(details.parameters_sha256) &&
					source.raw_sha256 === geometricInput &&
					details.input_bundle_sha256 === geometricInput &&
					details.weather_original_sha256 === pinned[key + ".weather.raw"];
			} else if (modelInput !== undefined) {
				const details = readObject(source.details);
				sourceMatches =
					(reference ||
						role === (dc ? "pv_available_dc" : "pv_available_ac")) &&
					source.origin === "modelled" &&
					details.model === "uniform_unshaded_pvlib_reference_v1" &&
					energyHash(modelInput) &&
					energyHash(pinned[key + ".pv_model_witness"]) &&
					source.raw_sha256 === modelInput &&
					details.input_bundle_sha256 === modelInput &&
					details.weather_original_sha256 === pinned[key + ".raw"];
				if (dc || unit)
					sourceMatches =
						sourceMatches &&
						details.output_boundary === DC_PV_STAGE &&
						details.ac_conversion_applied === false &&
						typeof details.converter_id === "string" &&
						details.converter_id.length > 0;
				if (unit)
					sourceMatches =
						sourceMatches && details.converter_id === unit.pv_converter_id;
				if (mixed && role === "reference_ac")
					sourceMatches =
						sourceMatches &&
						details.output_boundary ===
							"retained_selected_converter_ac_outputs" &&
						sameJson(
							details.converter_ids,
							readObject(result.model).ac_pv_converter_ids,
						);
			}
			energyRequire(
				profile.measurement === measured &&
					typeof profile.reconstructed_means === "boolean" &&
					positive(profile.effective_max_interval_seconds) &&
					positive(source.native_max_interval_seconds) &&
					sourceMatches,
			);
		}
	}
}
