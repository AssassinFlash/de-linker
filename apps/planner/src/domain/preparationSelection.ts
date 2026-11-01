import type { JsonObject, Project } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import type { PlanningRun } from "../data/planningProtocol.ts";
import { readRun, runTask } from "../data/planningProtocol.ts";
import { PV_TASK, WEATHER_TASK } from "../data/readPreparationResult.ts";
import { readObject } from "../data/readProtocol.ts";
import { sameJson } from "./draft.ts";
import { invalidateEnergyReplay } from "./energyScenario.ts";
import {
	forgetGeometricRoofMarker,
	geometricRoofAssetId,
	readSelections,
	rememberGeometricRoof,
} from "./profiles.ts";
import { readEquipmentPlant } from "./equipmentPlant.ts";
import { plantEnergyDraft } from "./plantEnergy.ts";
import {
	PVGIS_REFERENCE_TASK,
	referencePrepared,
	referenceRoof,
	assertReferenceAcTopology,
} from "./pvgisReference.ts";
import {
	GEOMETRIC_PV_TASK,
	compileGeometricPv,
	geometricPvDraft,
	GEOMETRIC_PV_MODEL_SERIES,
} from "./geometricPv.ts";

export function preparationPvRole(
	inputs: JsonObject,
): "pv_reference" | "pv_available_ac" {
	return inputs.equipment_plant !== undefined &&
		plantEnergyDraft(inputs, readEquipmentPlant(inputs.equipment_plant))
			.coupling === "plant_shared_dc"
		? "pv_reference"
		: "pv_available_ac";
}

/** Explicit selection changes only its role; the caller supplies current edits. */
export function selectPreparation(
	inputs: JsonObject,
	run: PlanningRun,
	historical: Project,
	ownedAsset: JsonObject,
): JsonObject {
	readRun(run, run.project_id, run.id);
	if (
		run.state !== "succeeded" ||
		!run.result ||
		historical.id !== run.project_id ||
		historical.revision !== run.revision ||
		historical.input_sha256 !== run.manifest.input_sha256 ||
		!sameJson(ownedAsset, run.result.prepared_asset)
	)
		throw new ApiError(502, "preparation_source_mismatch");
	const metadata = readObject(ownedAsset.metadata);
	const assetId = ownedAsset.id;
	if (typeof assetId !== "string" || !/^[a-f0-9]{32}$/.test(assetId))
		throw new ApiError(502, "preparation_source_mismatch");
	const task = runTask(run);
	if (task === WEATHER_TASK) {
		if (inputs.weather_acquisition === undefined)
			throw new ApiError(409, "preparation_source_changed");
		const requested = readObject(inputs.weather_acquisition);
		if (
			!sameJson(requested.request, metadata.weather_request) ||
			!sameJson(requested.interpretation, metadata.weather_interpretation)
		)
			throw new ApiError(409, "preparation_source_changed");
		return {
			...inputs,
			pv_preparation: { schema_version: 1, weather_asset_id: assetId },
		};
	}
	if (task === PVGIS_REFERENCE_TASK || task === GEOMETRIC_PV_TASK) {
		// Both reference methods publish a single AC profile and adopt it the
		// same way; only the frozen inputs that must still match differ. Each
		// guard keeps its own reader so a mismatched source is refused before
		// anything is returned.
		if (task === PVGIS_REFERENCE_TASK) {
			referenceRoof(inputs);
			if (
				!sameJson(inputs.geometry, historical.inputs.geometry) ||
				!sameJson(inputs.pvgis_reference, historical.inputs.pvgis_reference) ||
				!referencePrepared(inputs)
			)
				throw new ApiError(409, "preparation_source_changed");
		} else {
			compileGeometricPv(geometricPvDraft(inputs), inputs.geometry);
			if (
				!sameJson(inputs.geometry, historical.inputs.geometry) ||
				(geometricPvDraft(inputs).model === GEOMETRIC_PV_MODEL_SERIES &&
					(!sameJson(
						inputs.equipment_selection,
						historical.inputs.equipment_selection,
					) ||
						!sameJson(
							inputs.pv_string_plan,
							historical.inputs.pv_string_plan,
						) ||
						!sameJson(
							inputs.equipment_plant,
							historical.inputs.equipment_plant,
						) ||
						!sameJson(
							inputs.pv_plant_string_plan,
							historical.inputs.pv_plant_string_plan,
						))) ||
				!sameJson(
					inputs.geometric_pv_preparation,
					historical.inputs.geometric_pv_preparation,
				)
			)
				throw new ApiError(409, "preparation_source_changed");
		}
		assertReferenceAcTopology(inputs);
		const adopted = {
			...invalidateEnergyReplay(inputs),
			profile_selections: {
				schema_version: 1,
				selected: {
					...readSelections(inputs.profile_selections).selected,
					pv_available_ac: assetId,
				},
			},
		};
		// Only the geometric whole-roof profile is remembered, so a later
		// shared DC choice can drop it without comparing asset ids.
		return task === GEOMETRIC_PV_TASK
			? rememberGeometricRoof(adopted, assetId)
			: forgetGeometricRoofMarker(adopted);
	}
	if (
		task !== PV_TASK ||
		!sameJson(inputs.geometry, historical.inputs.geometry) ||
		!sameJson(inputs.pv_preparation, historical.inputs.pv_preparation) ||
		!sameJson(inputs.pv_generation, historical.inputs.pv_generation)
	)
		throw new ApiError(409, "preparation_source_changed");
	const chosen = { ...readSelections(inputs.profile_selections).selected };
	const jointDc = preparationPvRole(inputs) === "pv_reference";
	const geometric = geometricRoofAssetId(inputs);
	if (jointDc) {
		chosen.pv_reference = assetId;
		if (
			chosen.pv_available_ac === assetId ||
			chosen.pv_available_ac === geometric
		)
			delete chosen.pv_available_ac;
	} else chosen.pv_available_ac = assetId;
	const selected = {
		...invalidateEnergyReplay(inputs),
		profile_selections: {
			schema_version: 1,
			selected: chosen,
		},
	};
	return jointDc || chosen.pv_available_ac !== geometric
		? forgetGeometricRoofMarker(selected)
		: selected;
}
