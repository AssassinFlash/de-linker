import { ApiError } from "./protocol.ts";
import type { JsonObject } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import {
	BATTERY_FIELDS,
	readBatteryParameters,
} from "../domain/energyScenario.ts";
import { sameJson } from "../domain/draft.ts";

const hash = (value: unknown): value is string =>
	typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
const number = (value: unknown): value is number =>
	typeof value === "number" && Number.isFinite(value) && value >= 0;
const positive = (value: unknown): value is number =>
	number(value) && value > 0;
const utc = (value: unknown): value is string =>
	typeof value === "string" &&
	/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)$/.test(
		value,
	);
function require(condition: unknown): asserts condition {
	if (!condition) throw new ApiError(502, "invalid_run_result");
}

/** Validate the consumed frozen document before any component renders it.
 * This checks identity and shape; it never recalculates or repairs a result. */
export function readEnergyResult(
	value: unknown,
	run: JsonObject,
	manifest: JsonObject,
): JsonObject {
	try {
		const result = readObject(value),
			context = readObject(manifest.context),
			models = readObject(context.models),
			pinned = readObject(result.pinned_assets);
		require(
			run.state === "succeeded" &&
				hash(run.result_sha256) &&
				result.schema === 1 &&
				result.kind === "single_ac_energy_replay_v1" &&
				result.project_id === run.project_id &&
				result.revision === run.revision &&
				result.input_sha256 === manifest.input_sha256 &&
				result.manifest_sha256 === run.manifest_sha256 &&
				result.runtime_sha256 === context.code_sha256 &&
				hash(result.trace_sha256) &&
				typeof result.interval_count === "number" &&
				Number.isSafeInteger(result.interval_count) &&
				result.interval_count > 0,
		);
		const model = readObject(result.model);
		if (model.version !== "constant_window_single_ac_bus_v1")
			throw new ApiError(502, "unsupported_run_model");
		readBatteryParameters({
			schema_version: 1,
			model: model.version,
			parameter_basis: "explicit_scenario",
			...Object.fromEntries(BATTERY_FIELDS.map((key) => [key, model[key]])),
		});
		require(
			model.battery_export === "excluded_from_this_model" &&
				model.internal_loss_order ===
					"standing_loss_then_internal_aux_before_ac_flows" &&
				model.source_accounting === "proportional_mixing_v1" &&
				models.battery === model.version &&
				models.replay === result.kind &&
				models.source_accounting === model.source_accounting &&
				sameJson(pinned, context.assets) &&
				Object.values(pinned).every(hash) &&
				model.parameters_source_sha256 === pinned["battery.raw"] &&
				readObject(result.dependencies).energy_trace === result.trace_sha256,
		);
		for (const role of ["battery", "gross_load", "pv_available_ac", "aux_ac"])
			require(hash(pinned[role + ".raw"]) && hash(pinned[role + ".metadata"]));
		const batteryMetadata = readObject(result.battery_parameter_provenance),
			provenance = readObject(batteryMetadata.provenance);
		require(
			batteryMetadata.retention === "permanent" &&
				provenance.basis === "user_explicit_scenario_not_equipment_release" &&
				typeof provenance.label === "string" &&
				provenance.label.trim(),
		);
		for (const assessment of [
			result.equipment_release,
			result.country_assessment,
		])
			if (readObject(assessment).status !== "not_assessed")
				throw new ApiError(502, "unsupported_run_assessment");
		const metrics = readObject(result.metrics);
		for (const name of [
			"load_demand_kwh",
			"solar_load_kwh",
			"grid_import_kwh",
			"pv_generated_ac_kwh",
			"unserved_load_kwh",
		])
			require(number(metrics[name]));
		require(
			["gross_load", "critical_load", "mixed"].includes(
				String(metrics.load_measurement_scope),
			),
		);
		for (const name of ["solar_autarky", "pv_input_self_use"]) {
			const ratio = readObject(metrics[name]);
			require(
				ratio.value === null
					? typeof ratio.undefined_reason === "string" &&
							ratio.undefined_reason.length > 0
					: typeof ratio.value === "number" &&
							Number.isFinite(ratio.value) &&
							ratio.undefined_reason === null,
			);
		}
		const autarky = readObject(metrics.solar_autarky),
			pvUse = readObject(metrics.pv_input_self_use);
		const autarkyReason =
			metrics.load_measurement_scope !== "gross_load"
				? "requested_load_scope_is_not_whole_site_gross"
				: metrics.load_demand_kwh === 0
					? "gross_load_is_zero"
					: null;
		require(
			autarky.undefined_reason === autarkyReason &&
				(autarky.value === null) === (autarkyReason !== null),
		);
		require(
			pvUse.undefined_reason ===
				(metrics.pv_generated_ac_kwh === 0 ? "pv_generation_is_zero" : null) &&
				(pvUse.value === null) === (metrics.pv_generated_ac_kwh === 0),
		);
		const verification = readObject(result.verification),
			checks = verification.checks;
		require(
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
			require(
				typeof check.code === "string" &&
					check.code.length > 0 &&
					typeof check.passed === "boolean" &&
					number(check.worst_violation) &&
					number(check.allowance) &&
					number(check.arithmetic_allowance) &&
					["kW", "kWh"].includes(String(check.unit)) &&
					typeof check.at_interval === "number" &&
					Number.isSafeInteger(check.at_interval) &&
					check.at_interval >= 0 &&
					check.at_interval < result.interval_count,
			);
		}
		require(
			verification.passed ===
				(checks as readonly JsonObject[]).every(
					(check) => check.passed === true,
				),
		);
		const periods = readObject(result.profile_interpretation).operating_periods;
		require(Array.isArray(periods) && periods.length > 0);
		for (const raw of periods as readonly unknown[]) {
			const period = readObject(raw),
				profiles = readObject(period.profiles);
			require(
				utc(period.start_utc) &&
					utc(period.end_utc) &&
					["connected", "outage"].includes(String(period.mode)),
			);
			const expected =
				period.mode === "outage"
					? ["critical_load", "pv_available_ac", "aux_ac"]
					: ["gross_load", "pv_available_ac", "aux_ac"];
			require(Object.keys(profiles).sort().join() === expected.sort().join());
			for (const [role, rawProfile] of Object.entries(profiles)) {
				const profile = readObject(rawProfile),
					source = readObject(profile.source),
					modelInput = pinned[role + ".pv_model_inputs"];
				// A generated roof profile identifies its frozen model input
				// bundle as the series source. The asset's raw bytes remain the
				// original weather; CSV/system-output profiles identify raw bytes.
				let sourceMatches = source.raw_sha256 === pinned[role + ".raw"];
				if (modelInput !== undefined) {
					const details = readObject(source.details);
					sourceMatches =
						role === "pv_available_ac" &&
						source.origin === "modelled" &&
						details.model === "uniform_unshaded_pvlib_reference_v1" &&
						hash(modelInput) &&
						hash(pinned[role + ".pv_model_witness"]) &&
						source.raw_sha256 === modelInput &&
						details.input_bundle_sha256 === modelInput &&
						details.weather_original_sha256 === pinned[role + ".raw"];
				}
				require(
					profile.measurement === role &&
						typeof profile.reconstructed_means === "boolean" &&
						positive(profile.effective_max_interval_seconds) &&
						positive(source.native_max_interval_seconds) &&
						sourceMatches,
				);
			}
		}
		return result;
	} catch (error) {
		if (error instanceof ApiError && error.status === 502) throw error;
		throw new ApiError(502, "invalid_run_result");
	}
}
