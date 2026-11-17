import { readBrief } from "../domain/brief.ts";
import { sameJson } from "../domain/draft.ts";
import { changeEquipment } from "../domain/equipment.ts";
import { isStorageOnly, readScenarioDraft } from "../domain/energyScenario.ts";
import { selectPreparation } from "../domain/preparationSelection.ts";
import { activePvGeometry } from "../domain/solarSetup.ts";
import { moduleSummary } from "../domain/panelPoses.ts";
import {
	GEOMETRIC_PV_MODEL_SERIES,
	GEOMETRIC_PV_PURPOSE,
	geometricPvDraft,
} from "../domain/geometricPv.ts";
import {
	hasPlant,
	plantInputs,
	readPlantDraft,
} from "../domain/equipmentPlant.ts";
import {
	readAsset,
	readSelections,
	type ProfileAsset,
} from "../domain/profiles.ts";
import {
	assertReferenceAcTopology,
	compilePvgisReference,
	KNOWN_PV_MODEL,
	KNOWN_PV_PURPOSE,
	PVGIS_REFERENCE_TASK,
	PVGIS_REFERENCE_PURPOSE,
	readPvgisReference,
	referenceDraft,
	referenceRoof,
	referenceSite,
} from "../domain/pvgisReference.ts";
import {
	readRun,
	runPending,
	waitForRunPoll,
	type PlanningRun,
} from "./planningProtocol.ts";
import { ApiError, type JsonObject, type Project } from "./protocol.ts";
import { readObject, readProject } from "./readProtocol.ts";

type Query = (
	path: "assets/read" | "projects/read" | "runs/read",
	body: JsonObject,
	signal: AbortSignal,
) => Promise<unknown>;

function comparisonInputs(
	inputs: JsonObject,
	asset: ProfileAsset,
	power: number,
): JsonObject {
	const scope =
		inputs.brief === undefined ? null : readBrief(inputs.brief).system_scope;
	let next = inputs;
	if (scope === "new_pv_storage" || scope === "pv_only") {
		if (hasPlant(inputs)) {
			const plant = readPlantDraft(inputs);
			if (plant.requirements.pv_dc_kw !== power)
				next = plantInputs(inputs, {
					...plant,
					requirements: { ...plant.requirements, pv_dc_kw: power },
				});
		} else if (readObject(inputs.equipment_setup ?? {}).pv_dc_kw !== power) {
			next = changeEquipment(inputs, { pv_dc_kw: power });
		}
	}
	if (next.energy_scenario === undefined || next.backup_demand !== undefined)
		return next;
	const scenario = readScenarioDraft(next.energy_scenario);
	const { schedule } = scenario;
	if (!schedule.length || !schedule.some((period) => period.pv_enabled))
		return next;
	const interpretation = readObject(asset.metadata.interpretation);
	const pvStart = Date.parse(String(interpretation.start_utc));
	const pvEnd = Date.parse(String(interpretation.end_utc));
	const requestedStart = Date.parse(schedule[0]!.start_utc);
	const requestedEnd = Date.parse(schedule.at(-1)!.end_utc);
	// Missing schedule endpoints are validated by the existing comparison command.
	if (!Number.isFinite(requestedStart) || !Number.isFinite(requestedEnd))
		return next;
	if (requestedStart >= pvStart && requestedEnd <= pvEnd) return next;
	const start = Math.max(pvStart, requestedStart);
	const end = Math.min(pvEnd, requestedEnd);
	if (!(end > start)) throw new ApiError(422, "known_pv_no_common_period");
	return {
		...next,
		energy_scenario: {
			...scenario,
			schedule: schedule.flatMap((period) => {
				const periodStart = Date.parse(period.start_utc);
				const periodEnd = Date.parse(period.end_utc);
				if (periodEnd <= start || periodStart >= end) return [];
				return [
					{
						...period,
						start_utc:
							periodStart < start
								? new Date(start).toISOString()
								: period.start_utc,
						end_utc:
							periodEnd > end ? new Date(end).toISOString() : period.end_utc,
					},
				];
			}),
		},
	};
}

/** Resolve the owned AC source and check the current draft again before adopting it. */
export async function prepareKnownPvForComparison({
	inputs,
	projectId,
	query,
	save,
	start,
	signal,
}: {
	inputs: JsonObject;
	projectId: string;
	query: Query;
	save: () => Promise<Project | null>;
	start: (revision: number) => Promise<PlanningRun | undefined>;
	signal: AbortSignal;
}): Promise<((current: JsonObject) => JsonObject) | null> {
	if (isStorageOnly(inputs)) return null;
	const draft = referenceDraft(inputs);
	const known = draft.model === KNOWN_PV_MODEL;
	const layout =
		!known && inputs.geometry !== undefined
			? activePvGeometry(inputs.geometry)
			: null;
	const placed = layout?.arrays.length
		? moduleSummary(layout.geometry).stc_kwp
		: null;
	const selected = readSelections(inputs.profile_selections).selected
		.pv_available_ac;
	if (
		!known &&
		placed === null &&
		!selected &&
		inputs.pvgis_reference_setup === undefined &&
		inputs.pvgis_reference === undefined
	)
		return null;
	const assetRead = async (id: string) => {
		const value = readAsset(
			await query(
				"assets/read",
				{ schema_version: 1, project_id: projectId, asset_id: id },
				signal,
			),
			projectId,
		);
		if (value.id !== id) throw new ApiError(502, "preparation_source_mismatch");
		return value;
	};
	const unchanged = (current: JsonObject) => {
		signal.throwIfAborted();
		if (
			isStorageOnly(current) ||
			readSelections(current.profile_selections).selected.pv_available_ac !==
				selected ||
			(!known && !sameJson(current.geometry, inputs.geometry))
		)
			throw new ApiError(409, "preparation_source_changed");
	};
	const historicalInputs = async (asset: ProfileAsset) => {
		const revision = asset.metadata.derived_from_revision;
		const historical = readProject(
			await query(
				"projects/read",
				{
					schema_version: 1,
					project_id: projectId,
					revision: revision!,
				},
				signal,
			),
		);
		if (historical.id !== projectId || historical.revision !== revision)
			throw new ApiError(502, "preparation_source_mismatch");
		return historical.inputs;
	};
	const asset = selected ? await assetRead(selected) : null;
	const pvgis =
		asset?.purpose === KNOWN_PV_PURPOSE ||
		asset?.purpose === PVGIS_REFERENCE_PURPOSE;
	if (asset && !pvgis) {
		const keys =
			asset.purpose === GEOMETRIC_PV_PURPOSE
				? ["geometry", "geometric_pv_preparation"]
				: asset.purpose === "pvlib_reference_profile_v1"
					? ["geometry", "pv_preparation", "pv_generation"]
					: [];
		if (
			asset.purpose === GEOMETRIC_PV_PURPOSE &&
			geometricPvDraft(inputs).model === GEOMETRIC_PV_MODEL_SERIES
		)
			keys.push(
				"equipment_selection",
				"pv_string_plan",
				"equipment_plant",
				"pv_plant_string_plan",
			);
		const matches = (current: JsonObject) =>
			keys.every((key) => sameJson(current[key], inputs[key]));
		if (keys.length && !matches(await historicalInputs(asset)))
			throw new ApiError(409, "preparation_source_changed");
		if (placed === null && !keys.length) return null;
		return (current) => {
			unchanged(current);
			if (!matches(current))
				throw new ApiError(409, "preparation_source_changed");
			return placed === null
				? current
				: comparisonInputs(current, asset, placed);
		};
	}
	if (!known) {
		if (placed === null)
			throw new ApiError(422, "pvgis_reference_roof_required");
		referenceRoof(inputs);
	}
	const reference = compilePvgisReference(draft);
	const site = known ? referenceSite(inputs) : null;
	const power = known
		? draft.arrays!.reduce((sum, array) => sum + array.peak_power_kwp!, 0)
		: placed!;
	const matchesBasis = (current: JsonObject) =>
		known
			? sameJson(referenceSite(current), site)
			: sameJson(current.geometry, inputs.geometry);
	const checked = (current: JsonObject) => {
		unchanged(current);
		if (!sameJson(referenceDraft(current), draft) || !matchesBasis(current))
			throw new ApiError(409, "preparation_source_changed");
		assertReferenceAcTopology(current);
	};
	assertReferenceAcTopology(inputs);
	if (asset?.purpose === (known ? KNOWN_PV_PURPOSE : PVGIS_REFERENCE_PURPOSE)) {
		const historical = await historicalInputs(asset);
		if (
			sameJson(readPvgisReference(historical.pvgis_reference), reference) &&
			matchesBasis(historical)
		)
			return (current) => {
				checked(current);
				return comparisonInputs(current, asset, power);
			};
	}
	const saved = await save();
	signal.throwIfAborted();
	if (!saved) throw new ApiError(409, "known_pv_preparation_save_failed");
	if (
		saved.id !== projectId ||
		!sameJson(readPvgisReference(saved.inputs.pvgis_reference), reference) ||
		!matchesBasis(saved.inputs)
	)
		throw new ApiError(409, "preparation_source_changed");
	let run = await start(saved.revision);
	if (!run) throw new ApiError(503, "known_pv_preparation_failed");
	while (runPending(run.state)) {
		await waitForRunPoll(signal);
		run = readRun(
			await query("runs/read", { schema_version: 1, run_id: run.id }, signal),
			projectId,
			run.id,
			PVGIS_REFERENCE_TASK,
		);
	}
	signal.throwIfAborted();
	if (run.state !== "succeeded" || !run.result)
		throw new ApiError(422, "known_pv_preparation_failed");
	const preparedAsset = await assetRead(
		readAsset(run.result.prepared_asset, projectId).id,
	);
	const completed = run;
	return (current) => {
		checked(current);
		return comparisonInputs(
			selectPreparation(current, completed, saved, preparedAsset),
			preparedAsset,
			power,
		);
	};
}
