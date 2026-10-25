import { ApiError } from "./protocol.ts";
import type { JsonObject } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import {
	BATTERY_FIELDS,
	readBatteryParameters,
} from "../domain/energyScenario.ts";
import { sameJson } from "../domain/draft.ts";
import { readEquipmentSelection } from "../domain/equipment.ts";
import { readEquipmentAssessment } from "./readEquipmentResult.ts";
import {
	DC_ENERGY_TASK,
	DC_MODEL,
	DC_PV_STAGE,
	readDcParameters,
} from "../domain/dcEnergy.ts";

export function isEnergyTask(value: unknown): boolean {
	return value === "single_ac_energy_replay_v1" || value === DC_ENERGY_TASK;
}

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

function equipmentBinding(
	result: JsonObject,
	models: JsonObject,
	pinned: JsonObject,
	model: JsonObject,
	dc: boolean,
) {
	if (result.equipment_binding == null) {
		require(
			pinned["equipment.selection"] === undefined &&
				pinned["woo.equipment_inputs"] === undefined,
		);
		return;
	}
	const binding = readObject(result.equipment_binding),
		selection = readEquipmentSelection(binding.selection),
		assessment = readEquipmentAssessment(binding.assessment);
	require(
		binding.schema_version === 1 &&
			binding.model ===
				(dc
					? "selected_woo_dc_scenario_v1"
					: "selected_woo_scenario_envelope_v1") &&
			models.equipment_envelope === binding.model &&
			binding.performance_status === "not_established_by_scenario_envelope" &&
			hash(pinned["woo.equipment_inputs"]) &&
			hash(pinned["equipment.selection"]) &&
			binding.selection_sha256 === pinned["equipment.selection"] &&
			sameJson(binding.scenario_model, model),
	);
	const selected = new Set(Object.keys(selection.product_revisions));
	const products = assessment.selected_products as readonly JsonObject[];
	require(products.length === selected.size);
	for (const product of products) {
		const id = String(product.product_id);
		require(
			selected.delete(id) &&
				product.product_revision === selection.product_revisions[id],
		);
	}
	const checks = assessment.checks as readonly JsonObject[];
	const requiredChecks = [
		"scenario_operating_mode",
		"scenario_parameter_basis",
		"scenario_model_domain",
	];
	if (!dc) requiredChecks.push("continuous_battery_ac_charge");
	if (selection.battery_product_id !== null)
		requiredChecks.push("usable_energy", "continuous_battery_ac_output");
	require(
		requiredChecks.every((id) => checks.some((check) => check.id === id)),
	);
	for (const id of ["scenario_parameter_basis", "scenario_model_domain"])
		require(checks.find((check) => check.id === id)?.status === "unresolved");
	for (const check of checks) {
		for (const fact of check.facts as readonly JsonObject[]) {
			if (fact.source === null) continue;
			const source = readObject(fact.source);
			require(
				typeof source.product_id === "number" &&
					Object.hasOwn(
						selection.product_revisions,
						String(source.product_id),
					) &&
					source.product_revision ===
						selection.product_revisions[String(source.product_id)] &&
					hash(source.figure_sha256) &&
					hash(source.document_revision) &&
					hash(source.blob_sha256),
			);
		}
	}
	for (const [id, field] of [
		["usable_energy", "usable_window_kwh"],
		["continuous_battery_ac_output", "discharge_ac_kw"],
		["continuous_battery_ac_charge", "charge_ac_kw"],
	] as const) {
		if (dc && id !== "usable_energy") continue;
		const check = checks.find((check) => check.id === id);
		if (check) require(check.required === model[field]);
	}
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
		const dc = result.kind === DC_ENERGY_TASK;
		require(
			run.state === "succeeded" &&
				hash(run.result_sha256) &&
				result.schema === 1 &&
				isEnergyTask(result.kind) &&
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
		if (model.version !== (dc ? DC_MODEL : "constant_window_single_ac_bus_v1"))
			throw new ApiError(502, "unsupported_run_model");
		if (dc) {
			const prepared = readDcParameters(result.prepared_dc_parameters),
				losses = readObject(prepared.loss_scenario);
			for (const name of ["connected_bridge", "outage_bridge"]) {
				if (model[name] === null) continue;
				const bridge = readObject(model[name]);
				require(
					bridge.eta_forward === losses.eta_inverter_forward &&
						(bridge.reverse_supported !== true ||
							bridge.eta_reverse === losses.eta_inverter_reverse),
				);
			}

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
			require(
				number(model.charge_terminal_kw) &&
					number(model.discharge_terminal_kw) &&
					hash(pinned["battery.dc_prepared_parameters"]) &&
					hash(pinned["battery.dc_woo_inputs"]) &&
					prepared.selection_sha256 === pinned["equipment.selection"],
			);
			const binding = readObject(result.equipment_binding),
				selection = readEquipmentSelection(binding.selection);
			require(
				sameJson(prepared.product_revisions, selection.product_revisions) &&
					readObject(model.selected_port).id === losses.battery_port_id,
			);
		} else
			readBatteryParameters({
				schema_version: 1,
				model: model.version,
				parameter_basis: "explicit_scenario",
				...Object.fromEntries(BATTERY_FIELDS.map((key) => [key, model[key]])),
			});
		require(
			model.battery_export === "excluded_from_this_model" &&
				model.internal_loss_order ===
					(dc
						? "standing_loss_then_internal_aux_before_dc_flows"
						: "standing_loss_then_internal_aux_before_ac_flows") &&
				model.source_accounting === "proportional_mixing_v1" &&
				models.battery === model.version &&
				models.replay === result.kind &&
				models.source_accounting === model.source_accounting &&
				sameJson(pinned, context.assets) &&
				Object.values(pinned).every(hash) &&
				model.parameters_source_sha256 ===
					pinned[dc ? "battery.dc_prepared_parameters" : "battery.raw"] &&
				readObject(result.dependencies).energy_trace === result.trace_sha256,
		);
		for (const role of [
			"battery",
			"gross_load",
			dc ? "pv_available_dc" : "pv_available_ac",
			"aux_ac",
		])
			require(hash(pinned[role + ".raw"]) && hash(pinned[role + ".metadata"]));
		equipmentBinding(result, models, pinned, model, dc);
		const batteryMetadata = readObject(result.battery_parameter_provenance),
			provenance = readObject(batteryMetadata.provenance);
		if (dc) {
			const dependencies = readObject(batteryMetadata.dependencies);
			require(
				Object.keys(dependencies).sort().join() ===
					"dc_prepared_parameters,dc_woo_inputs" &&
					dependencies.dc_prepared_parameters ===
						pinned["battery.dc_prepared_parameters"] &&
					dependencies.dc_woo_inputs === pinned["battery.dc_woo_inputs"],
			);
		}
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
			dc ? "pv_generated_dc_kwh" : "pv_generated_ac_kwh",
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
			pvUse = readObject(metrics.pv_input_self_use),
			generation = metrics[dc ? "pv_generated_dc_kwh" : "pv_generated_ac_kwh"];
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
				(generation === 0 ? "pv_generation_is_zero" : null) &&
				(pvUse.value === null) === (generation === 0),
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
					? [
							"critical_load",
							dc ? "pv_available_dc" : "pv_available_ac",
							"aux_ac",
						]
					: [
							"gross_load",
							dc ? "pv_available_dc" : "pv_available_ac",
							"aux_ac",
						];
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
						role === (dc ? "pv_available_dc" : "pv_available_ac") &&
						source.origin === "modelled" &&
						details.model === "uniform_unshaded_pvlib_reference_v1" &&
						hash(modelInput) &&
						hash(pinned[role + ".pv_model_witness"]) &&
						source.raw_sha256 === modelInput &&
						details.input_bundle_sha256 === modelInput &&
						details.weather_original_sha256 === pinned[role + ".raw"];
					if (dc)
						sourceMatches =
							sourceMatches &&
							details.output_boundary === DC_PV_STAGE &&
							details.ac_conversion_applied === false &&
							typeof details.converter_id === "string" &&
							details.converter_id.length > 0;
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
