import {
	restoreComparisonModels,
	sameEquipmentDemand,
} from "../domain/currentCalculation.ts";
import { sameJson } from "../domain/draft.ts";
import {
	GEOMETRIC_PV_MODEL_SERIES,
	GEOMETRIC_PV_TASK,
} from "../domain/geometricPv.ts";
import {
	KNOWN_PV_MODEL,
	KNOWN_PV_PURPOSE,
	PVGIS_REFERENCE_PURPOSE,
	PVGIS_REFERENCE_TASK,
} from "../domain/pvgisReference.ts";
import { readAsset, readSelections } from "../domain/profiles.ts";
import { DC_PLANT_ENERGY_TASK } from "../domain/plantEnergy.ts";
import {
	RUN_OPERATIONS,
	readRun,
	readRunInputs,
	readRunPage,
	runPending,
	type RunSummary,
} from "./planningProtocol.ts";
import type { ReportOptions } from "./planningReport.ts";
import type { JsonObject, Project } from "./protocol.ts";
import { ApiError } from "./protocol.ts";
import { isEnergyTask } from "./readEnergyResult.ts";
import { readObject, readProject } from "./readProtocol.ts";

const equipment = [
	"equipment_setup",
	"equipment_selection",
	"equipment_plant_setup",
	"equipment_plant",
];
export function hasReportWiring(inputs: JsonObject): boolean {
	return inputs.pv_string_plan != null || inputs.pv_plant_string_plan != null;
}

const wiring = ["geometry", "pv_string_plan", "pv_plant_string_plan"];
const equipmentEvidence = [
	"grid_connection",
	"country_rule_inputs",
	"equipment_condition_inputs",
];
const energy = [
	"energy_scenario",
	"energy_plant_setup",
	"profile_selections",
	"backup_demand",
	...equipment,
];
const pvDependencies = [
	"geometry",
	"pvgis_reference",
	"pv_generation",
	"pv_preparation",
	"geometric_pv_preparation",
	"weather_acquisition",
	"pv_string_plan",
	"pv_plant_string_plan",
];
const weatherPv = RUN_OPERATIONS["runs/pv"];
const checkEquipment = RUN_OPERATIONS["runs/check-equipment"];
const searchEquipment = RUN_OPERATIONS["runs/find-equipment"];

function matches(a: JsonObject, b: JsonObject, fields: readonly string[]) {
	return fields.every((key) => sameJson(a[key] ?? null, b[key] ?? null));
}

function site(inputs: JsonObject) {
	return readObject(readObject(inputs.brief ?? {}).site ?? {});
}

function scope(inputs: JsonObject) {
	return readObject(inputs.brief ?? {}).system_scope ?? null;
}

function sameSite(a: JsonObject, b: JsonObject) {
	const left = site(a),
		right = site(b);
	return sameJson(
		{ ...left, postal_code: left.postal_code ?? null },
		{ ...right, postal_code: right.postal_code ?? null },
	);
}

function isSharedDcSetup(inputs: JsonObject): boolean {
	return (
		readObject(inputs.energy_plant_setup ?? {}).coupling === "plant_shared_dc"
	);
}

export function sameEnergyReportInputs(
	previous: JsonObject,
	inputs: JsonObject,
): boolean {
	return (
		scope(previous) === scope(inputs) &&
		(!isSharedDcSetup(inputs) || sameSite(previous, inputs)) &&
		matches(previous, inputs, [
			...energy,
			...equipmentEvidence,
			...pvDependencies,
			"energy_replay",
			"energy_plant",
		])
	);
}

export function sharedDcReportRun(inputs: JsonObject): string | null {
	const id = inputs.shared_dc_energy_run_id;
	return isSharedDcSetup(inputs) &&
		typeof id === "string" &&
		/^[a-f0-9]{32}$/.test(id)
		? id
		: null;
}

export async function configuratorReportSources({
	project,
	pageSize,
	query,
	signal,
}: {
	project: Project;
	pageSize: number;
	query: (
		path:
			| "projects/runs"
			| "projects/read"
			| "runs/read"
			| "runs/inputs"
			| "assets/read",
		body: JsonObject,
		signal: AbortSignal,
	) => Promise<unknown>;
	signal: AbortSignal;
}): Promise<{
	options: Pick<
		ReportOptions,
		"energy_run_id" | "pv_run_id" | "equipment_run_id"
	>;
	pendingEquipmentCheck: string | null;
}> {
	const inputs = project.inputs;
	const hasWiring = hasReportWiring(inputs);
	const needsEquipment =
		(inputs.equipment_candidate == null || hasWiring) &&
		equipment.some((key) => inputs[key] != null);
	const canUseRetained =
		!hasWiring &&
		readObject(inputs.existing_system ?? {}).keep_inverter === true;
	const adoptedDc = sharedDcReportRun(inputs);
	const needsEnergy = [
		"energy_scenario",
		"energy_plant_setup",
		"energy_replay",
		"energy_plant",
	].some((key) => inputs[key] != null);
	const selected = readSelections(inputs.profile_selections).selected;
	const selectedPv = isSharedDcSetup(inputs)
		? selected.pv_reference
		: (selected.pv_available_ac ?? selected.pv_reference);
	const needsPv =
		scope(inputs) !== "storage_only" &&
		["pvgis_reference", "pv_generation", "geometric_pv_preparation"].some(
			(key) => inputs[key] != null,
		);
	const base = { schema_version: 1, project_id: project.id };
	let pvRun: string | null = null,
		pvAsset: unknown = null;
	async function isManagedPvgis(id: string) {
		const asset = readAsset(
			await query("assets/read", { ...base, asset_id: id }, signal),
			project.id,
		);
		if (asset.id !== id) throw new ApiError(502, "run_source_mismatch");
		return (
			asset.purpose === KNOWN_PV_PURPOSE ||
			asset.purpose === PVGIS_REFERENCE_PURPOSE
		);
	}
	if (inputs.equipment_candidate != null) {
		const choice = readObject(inputs.equipment_candidate);
		const run = readRun(
			await query(
				"runs/read",
				{ schema_version: 1, run_id: choice.run_id! },
				signal,
			),
			project.id,
			String(choice.run_id),
			searchEquipment,
		);
		const frozen = readRunInputs(
			await query("runs/inputs", { ...base, run_id: run.id }, signal),
			run,
		);
		if (
			!sameEquipmentDemand(
				restoreComparisonModels(inputs, frozen),
				frozen,
				!hasWiring,
			)
		)
			throw new ApiError(409, "equipment_selection_changed");
		if (
			needsPv &&
			run.state === "succeeded" &&
			run.result?.prepared_asset != null
		) {
			const asset = readObject(run.result.prepared_asset);
			if (asset.project_id !== project.id)
				throw new ApiError(502, "run_source_mismatch");
			const known =
				readObject(inputs.pvgis_reference ?? {}).model === KNOWN_PV_MODEL;
			const selectedPv = selected.pv_available_ac ?? selected.pv_reference;
			if (
				asset.purpose ===
					(known ? KNOWN_PV_PURPOSE : PVGIS_REFERENCE_PURPOSE) &&
				matches(
					frozen,
					inputs,
					known ? ["pvgis_reference"] : ["geometry", "pvgis_reference"],
				) &&
				(!known || sameSite(frozen, inputs))
			) {
				const canUsePrepared =
					selectedPv == null ||
					selectedPv === asset.id ||
					(selected.pv_reference == null && (await isManagedPvgis(selectedPv)));
				if (canUsePrepared) {
					pvRun = run.id;
					pvAsset = asset.id;
				}
			}
		}
	}
	const revisions = new Map<number, Promise<Project>>();
	async function authored(row: RunSummary) {
		if (row.revision === project.revision) return project;
		let cached = revisions.get(row.revision);
		if (!cached) {
			cached = query(
				"projects/read",
				{ ...base, revision: row.revision },
				signal,
			).then(readProject);
			revisions.set(row.revision, cached);
		}
		const previous = await cached;
		if (previous.id !== project.id || previous.revision !== row.revision)
			throw new ApiError(502, "run_source_mismatch");
		return previous;
	}
	const completed = async (
		row: RunSummary,
		kind: Parameters<typeof readRun>[3],
		snapshot: Project,
	) => {
		const run = readRun(
			await query("runs/read", { schema_version: 1, run_id: row.id }, signal),
			project.id,
			row.id,
			kind,
		);
		if (
			run.revision !== row.revision ||
			run.manifest_sha256 !== row.manifest_sha256 ||
			run.result_sha256 !== row.result_sha256 ||
			run.manifest.input_sha256 !== snapshot.input_sha256
		)
			throw new ApiError(502, "run_source_mismatch");
		return run.state === "succeeded" ? run.result : null;
	};
	const frozen = async (row: RunSummary) =>
		readRunInputs(
			await query("runs/inputs", { ...base, run_id: row.id }, signal),
			row,
		);
	let energyRun: string | null = null,
		energyPv: unknown = null,
		equipmentRun: string | null = null,
		pendingEquipmentCheck: string | null = null;
	let cursor: { before_created_at: number | null; before_id: string | null } = {
		before_created_at: null,
		before_id: null,
	};
	while (
		(needsEnergy && !energyRun) ||
		(needsPv && !pvRun) ||
		((needsEquipment || canUseRetained) && !equipmentRun)
	) {
		const page = readRunPage(
			await query(
				"projects/runs",
				{ ...base, page_size: pageSize, ...cursor },
				signal,
			),
			project.id,
		);
		for (const row of page.items) {
			const kind = row.task_kind;
			if (
				needsEquipment &&
				!pendingEquipmentCheck &&
				kind === checkEquipment &&
				row.revision === project.revision &&
				runPending(row.state)
			)
				pendingEquipmentCheck = row.id;
			if (row.state !== "succeeded" || row.revision > project.revision)
				continue;
			if (
				canUseRetained &&
				!equipmentRun &&
				kind === searchEquipment &&
				row.revision === project.revision
			) {
				const result = await completed(row, kind, project);
				if (
					result?.retained_inverter != null &&
					sameJson(
						readObject(result.retained_inverter).existing_system,
						inputs.existing_system,
					)
				)
					equipmentRun = row.id;
				continue;
			}
			if (needsEnergy && !energyRun && isEnergyTask(kind)) {
				if (
					adoptedDc !== null &&
					(kind !== DC_PLANT_ENERGY_TASK || row.id !== adoptedDc)
				)
					continue;
				const previous = (await authored(row)).inputs;
				if (!sameEnergyReportInputs(previous, inputs)) continue;
				const execution = await frozen(row);
				if (adoptedDc !== null && execution.energy_plant == null)
					throw new ApiError(502, "run_source_mismatch");
				const joint = execution.energy_plant != null;
				const scenario = readObject(
					execution[joint ? "energy_plant" : "energy_replay"],
				);
				const pv =
					scenario.coupling === "plant_shared_dc"
						? scenario.pv_reference_asset_id
						: scenario.pv_available_asset_id;
				if (
					adoptedDc !== null &&
					(scenario.coupling !== "plant_shared_dc" ||
						(pv ?? null) !== (selected.pv_reference ?? null))
				)
					throw new ApiError(502, "run_source_mismatch");
				if (pv != null && !sameSite(previous, inputs)) continue;
				energyRun = row.id;
				energyPv = pv;
			} else if (needsEquipment && !equipmentRun && kind === checkEquipment) {
				const previous = (await authored(row)).inputs;
				if (
					scope(previous) !== scope(inputs) ||
					!matches(previous, inputs, [
						...equipment,
						...equipmentEvidence,
						"backup_demand",
						...wiring,
					]) ||
					site(previous).country_code !== site(inputs).country_code ||
					(inputs.pv_plant_string_plan != null &&
						!matches(previous, inputs, ["installation"]))
				)
					continue;
				const execution = await frozen(row);
				if (
					execution.equipment_selection == null &&
					execution.equipment_plant == null
				)
					continue;
				if (hasWiring) {
					const result = await completed(
						row,
						checkEquipment,
						await authored(row),
					);
					if (!result || readObject(result.assessment).pv_electrical == null)
						continue;
				}
				equipmentRun = row.id;
			} else if (
				needsPv &&
				!pvRun &&
				(kind === PVGIS_REFERENCE_TASK ||
					kind === GEOMETRIC_PV_TASK ||
					kind === weatherPv)
			) {
				const previous = await authored(row);
				const known =
					readObject(previous.inputs.pvgis_reference ?? {}).model ===
					KNOWN_PV_MODEL;
				const fields =
					kind === PVGIS_REFERENCE_TASK
						? known
							? ["pvgis_reference"]
							: ["geometry", "pvgis_reference"]
						: kind === weatherPv
							? [
									"geometry",
									"pv_generation",
									"pv_preparation",
									"weather_acquisition",
								]
							: ["geometry", "geometric_pv_preparation", "weather_acquisition"];
				if (
					!matches(previous.inputs, inputs, fields) ||
					(known && !sameSite(previous.inputs, inputs))
				)
					continue;
				const result = await completed(row, kind, previous);
				if (!result) continue;
				const asset = readObject(result.prepared_asset);
				if (asset.project_id !== project.id)
					throw new ApiError(502, "run_source_mismatch");
				if (known && asset.purpose !== KNOWN_PV_PURPOSE) continue;
				if (
					result.model === GEOMETRIC_PV_MODEL_SERIES &&
					!matches(previous.inputs, inputs, [
						"equipment_selection",
						"equipment_plant",
						"pv_string_plan",
						"pv_plant_string_plan",
					])
				)
					continue;
				if (selectedPv != null && selectedPv !== asset.id) continue;
				pvRun = row.id;
				pvAsset = asset.id;
			}
		}
		if (!page.next) break;
		cursor = page.next;
	}
	return {
		options: {
			energy_run_id: energyRun,
			pv_run_id: energyRun && energyPv !== pvAsset ? null : pvRun,
			equipment_run_id: equipmentRun,
		},
		pendingEquipmentCheck,
	};
}
