import { verifyDcModel } from "./readDcEnergyModel.ts";
import { verifyEnergyDetails } from "./readEnergyDetails.ts";
import { readPlantEnergyResult } from "./readPlantEnergyResult.ts";
import { isPlantEnergyTask } from "../domain/plantEnergy.ts";
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
	readDcParameters,
} from "../domain/dcEnergy.ts";

export function isEnergyTask(value: unknown): boolean {
	return (
		value === "single_ac_energy_replay_v1" ||
		value === DC_ENERGY_TASK ||
		isPlantEnergyTask(value)
	);
}

const hash = (value: unknown): value is string =>
	typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
const number = (value: unknown): value is number =>
	typeof value === "number" && Number.isFinite(value) && value >= 0;
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
		if (isPlantEnergyTask(result.kind))
			return readPlantEnergyResult(result, run, manifest);
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
			const prepared = readDcParameters(result.prepared_dc_parameters);
			verifyDcModel(model, prepared);
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
					readObject(model.selected_port).id ===
						readObject(prepared.loss_scenario).battery_port_id,
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
		verifyEnergyDetails(result, pinned, dc);
		return result;
	} catch (error) {
		if (error instanceof ApiError && error.status === 502) throw error;
		throw new ApiError(502, "invalid_run_result");
	}
}
