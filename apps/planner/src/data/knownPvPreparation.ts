import { readBrief } from "../domain/brief.ts";
import { sameJson } from "../domain/draft.ts";
import { changeEquipment } from "../domain/equipment.ts";
import { isStorageOnly, readScenarioDraft } from "../domain/energyScenario.ts";
import { selectPreparation } from "../domain/preparationSelection.ts";
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
	referenceDraft,
	referenceSite,
} from "../domain/pvgisReference.ts";
import { readRun, runPending, type PlanningRun } from "./planningProtocol.ts";
import { ApiError, type JsonObject, type Project } from "./protocol.ts";
import { readObject, readProject } from "./readProtocol.ts";

type Query = (
	path: "assets/read" | "projects/read" | "runs/read",
	body: JsonObject,
	signal: AbortSignal,
) => Promise<unknown>;

function waitForPoll(signal: AbortSignal): Promise<void> {
	signal.throwIfAborted();
	return new Promise((resolve, reject) => {
		const timer = setTimeout(() => {
			signal.removeEventListener("abort", abort);
			resolve();
		}, 1000);
		function abort() {
			clearTimeout(timer);
			reject(signal.reason);
		}
		signal.addEventListener("abort", abort, { once: true });
	});
}

function comparisonInputs(inputs: JsonObject, asset: ProfileAsset): JsonObject {
	const scope = readBrief(inputs.brief).system_scope;
	const draft = referenceDraft(inputs);
	let next = inputs;
	if (
		(scope === "new_pv_storage" || scope === "pv_only") &&
		inputs.equipment_plant_setup === undefined &&
		inputs.equipment_plant === undefined
	) {
		const power = draft.arrays!.reduce(
			(sum, array) => sum + array.peak_power_kwp!,
			0,
		);
		if (readObject(inputs.equipment_setup ?? {}).pv_dc_kw !== power)
			next = changeEquipment(inputs, { pv_dc_kw: power });
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
	if (draft.model !== KNOWN_PV_MODEL) return null;
	const selected = readSelections(inputs.profile_selections).selected
		.pv_available_ac;
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
	const checked = (current: JsonObject) => {
		signal.throwIfAborted();
		if (
			isStorageOnly(current) ||
			readSelections(current.profile_selections).selected.pv_available_ac !==
				selected ||
			!sameJson(
				compilePvgisReference(referenceDraft(current)),
				compilePvgisReference(draft),
			) ||
			!sameJson(referenceSite(current), referenceSite(inputs))
		)
			throw new ApiError(409, "preparation_source_changed");
		assertReferenceAcTopology(current);
	};
	if (selected) {
		const asset = await assetRead(selected);
		if (asset.purpose !== KNOWN_PV_PURPOSE) return null;
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
		if (
			sameJson(
				compilePvgisReference(draft),
				historical.inputs.pvgis_reference,
			) &&
			sameJson(referenceSite(inputs), referenceSite(historical.inputs))
		) {
			return (current) => {
				checked(current);
				return comparisonInputs(current, asset);
			};
		}
	}
	const reference = compilePvgisReference(draft);
	const site = referenceSite(inputs);
	assertReferenceAcTopology(inputs);
	const saved = await save();
	signal.throwIfAborted();
	if (!saved) throw new ApiError(409, "known_pv_preparation_save_failed");
	if (
		saved.id !== projectId ||
		!sameJson(saved.inputs.pvgis_reference, reference) ||
		!sameJson(referenceSite(saved.inputs), site)
	)
		throw new ApiError(409, "preparation_source_changed");
	let run = await start(saved.revision);
	if (!run) throw new ApiError(503, "known_pv_preparation_failed");
	while (runPending(run.state)) {
		await waitForPoll(signal);
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
	const asset = await assetRead(
		readAsset(run.result.prepared_asset, projectId).id,
	);
	const completed = run;
	return (current) => {
		checked(current);
		return comparisonInputs(
			selectPreparation(current, completed, saved, asset),
			asset,
		);
	};
}
