import type { JsonObject } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import { readEquipmentAssessment } from "./readEquipmentResult.ts";
import { readEquipmentPlant } from "../domain/equipmentPlant.ts";
import { readDcParameters } from "../domain/dcEnergy.ts";
import {
	BATTERY_FIELDS,
	readBatteryParameters,
} from "../domain/energyScenario.ts";
import {
	PLANT_ENERGY_MODEL,
	PLANT_ENERGY_TASK,
} from "../domain/plantEnergy.ts";
import { sameJson } from "../domain/draft.ts";
import {
	energyHash as hash,
	energyNumber as number,
	energyRequire as require,
	verifyEnergyDetails,
} from "./readEnergyDetails.ts";

/** Verify consumed identities and source bindings without recalculating physics. */
export function readPlantEnergyResult(
	result: JsonObject,
	run: JsonObject,
	manifest: JsonObject,
): JsonObject {
	const context = readObject(manifest.context),
		models = readObject(context.models),
		pinned = readObject(result.pinned_assets),
		model = readObject(result.model);
	require(
		run.state === "succeeded" &&
			hash(run.result_sha256) &&
			result.schema === 1 &&
			result.kind === PLANT_ENERGY_TASK &&
			result.project_id === run.project_id &&
			result.revision === run.revision &&
			result.input_sha256 === manifest.input_sha256 &&
			result.manifest_sha256 === run.manifest_sha256 &&
			result.runtime_sha256 === context.code_sha256 &&
			hash(result.trace_sha256) &&
			Number.isSafeInteger(result.interval_count) &&
			Number(result.interval_count) > 0,
	);
	require(
		model.version === PLANT_ENERGY_MODEL &&
			models.battery === model.version &&
			models.replay === result.kind &&
			model.source_accounting ===
				"proportional_mixing_per_unit_and_common_ac_bus_v1" &&
			models.source_accounting === model.source_accounting &&
			model.pv_boundary ===
				"independent_ac_generation; converter_dc_pv_inputs_unused" &&
			sameJson(pinned, context.assets) &&
			Object.values(pinned).every(hash) &&
			readObject(result.dependencies).energy_trace === result.trace_sha256,
	);
	const binding = readObject(result.equipment_binding),
		plant = readEquipmentPlant(binding.plant),
		assessment = readEquipmentAssessment(binding.assessment);
	require(
		binding.schema_version === 1 &&
			binding.model === "selected_woo_plant_ac_scenario_v1" &&
			models.equipment_envelope === binding.model &&
			binding.plant_sha256 === pinned["equipment.plant"] &&
			hash(pinned["equipment.plant"]) &&
			hash(pinned["woo.equipment_inputs"]) &&
			sameJson(binding.scenario_model, model) &&
			binding.performance_status === "not_established_by_scenario_envelope",
	);
	const revisions = new Map<number, string>();
	for (const unit of plant.units)
		for (const [id, revision] of Object.entries(
			unit.selection.product_revisions,
		))
			revisions.set(Number(id), revision);
	for (const group of plant.parallel_groups)
		if (
			group.controller_product_id !== null &&
			group.controller_revision !== null
		)
			revisions.set(group.controller_product_id, group.controller_revision);
	const products = assessment.selected_products as readonly JsonObject[];
	require(products.length === revisions.size);
	for (const product of products) {
		require(
			revisions.get(Number(product.product_id)) === product.product_revision,
		);
		revisions.delete(Number(product.product_id));
	}
	const sources = readObject(result.parameter_sources),
		pool = readObject(sources.pool);
	require(
		Array.isArray(sources.units) &&
			Array.isArray(model.units) &&
			sources.units.length === plant.units.length &&
			model.units.length === plant.units.length,
	);
	const parameterUnits = sources.units as readonly JsonObject[],
		unitModels = model.units as readonly JsonObject[];
	require(
		new Set(parameterUnits.map((u) => u.unit_id)).size === plant.units.length &&
			new Set(unitModels.map((u) => u.unit_id)).size === plant.units.length,
	);
	for (const unit of plant.units) {
		const entry = parameterUnits.find((u) => u.unit_id === unit.id),
			unitModel = unitModels.find((u) => u.unit_id === unit.id),
			prefix = `unit:${unit.id}:battery.`;
		require(
			entry &&
				unitModel &&
				hash(entry.parameter_sha256) &&
				entry.parameter_sha256 === pinned[prefix + "dc_prepared_parameters"] &&
				typeof entry.asset_id === "string" &&
				/^[a-f0-9]{32}$/.test(entry.asset_id),
		);
		for (const key of [
			"raw",
			"metadata",
			"dc_prepared_parameters",
			"dc_woo_inputs",
		])
			require(hash(pinned[prefix + key]));
		const proof = readDcParameters(pool[entry.parameter_sha256]);
		require(
			sameJson(proof.product_revisions, unit.selection.product_revisions),
		);
		const provenance = readObject(entry.provenance);
		require(
			provenance.basis === "user_explicit_scenario_not_equipment_release" &&
				typeof provenance.label === "string" &&
				provenance.label.trim().length > 0,
		);
		for (const mode of ["connected", "outage"]) {
			if (mode === "outage" && unitModel[mode] === null) continue;
			const equivalent = readObject(unitModel[mode]);
			readBatteryParameters({
				schema_version: 1,
				model: "constant_window_single_ac_bus_v1",
				parameter_basis: "explicit_scenario",
				...Object.fromEntries(
					BATTERY_FIELDS.map((key) => [key, equivalent[key]]),
				),
			});
			require(
				equivalent.parameters_source_sha256 === entry.parameter_sha256 &&
					equivalent.usable_window_kwh === proof.usable_window_kwh,
			);
		}
	}
	for (const role of ["gross_load", "pv_available_ac", "aux_ac"])
		require(hash(pinned[role + ".raw"]) && hash(pinned[role + ".metadata"]));
	const metrics = readObject(result.metrics);
	require(
		Array.isArray(metrics.units) &&
			metrics.units.length === plant.units.length &&
			new Set(metrics.units.map((u) => readObject(u).unit_id)).size ===
				plant.units.length,
	);
	for (const raw of metrics.units) {
		const unit = readObject(raw);
		require(
			plant.units.some((u) => u.id === unit.unit_id) &&
				number(unit.usable_window_kwh) &&
				number(unit.charge_ac_kwh) &&
				number(unit.discharge_ac_kwh),
		);
		for (const side of ["stored_initial", "stored_final"]) {
			const inventory = readObject(unit[side]);
			for (const key of ["pv_kwh", "grid_kwh", "initial_unknown_kwh"])
				require(number(inventory[key]));
		}
	}
	const verification = readObject(result.verification);
	require(
		verification.physical_passed === true &&
			Array.isArray(verification.task_codes),
	);
	verifyEnergyDetails(result, pinned, false);
	return result;
}
