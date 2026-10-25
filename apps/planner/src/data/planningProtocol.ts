import {
	REPORT_TASK,
	readReportOptions,
	readReportResult,
} from "./planningReport.ts";
import { ApiError } from "./protocol.ts";
import type { JsonObject } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import { readBatteryParameters } from "../domain/energyScenario.ts";
import { readEnergyResult, isEnergyTask } from "./readEnergyResult.ts";
import {
	DC_MODEL,
	DC_ENERGY_TASK,
	readDcLossScenario,
} from "../domain/dcEnergy.ts";
import { readPreparationResult } from "./readPreparationResult.ts";
import { SEARCH_TASK, readEquipmentSearchResult } from "./equipmentSearch.ts";
import { EQUIPMENT_TASK, readEquipmentResult } from "./readEquipmentResult.ts";

export const RUN_OPERATIONS = {
	"runs/energy": "single_ac_energy_replay_v1",
	"runs/pv": "prepare_roof_pv_reference_v1",
	"runs/weather": "acquire_pvgis_tmy_weather_v1",
	"runs/equipment": EQUIPMENT_TASK,
	"runs/equipment-search": SEARCH_TASK,
	"runs/report": REPORT_TASK,
} as const;
export type RunOperation = keyof typeof RUN_OPERATIONS;
export type TaskKind =
	(typeof RUN_OPERATIONS)[RunOperation] | typeof DC_ENERGY_TASK;
export type PlanningOperation =
	"battery/scenario" | "draft/apply" | RunOperation;
export function isPlanningOperation(
	value: unknown,
): value is PlanningOperation {
	return (
		value === "battery/scenario" ||
		value === "draft/apply" ||
		(typeof value === "string" && Object.hasOwn(RUN_OPERATIONS, value))
	);
}
/** The immutable manifest identifies the task, independent of its state/result. */
export function runTask(run: Pick<PlanningRun, "manifest">): string | null {
	const context = readObject(run.manifest.context),
		parameters = readObject(context.parameters);
	return typeof parameters.kind === "string" ? parameters.kind : null;
}
export const RUN_STATES = [
	"queued",
	"running",
	"retry_wait",
	"succeeded",
	"failed",
	"cancelled",
] as const;
export type RunState = (typeof RUN_STATES)[number];
export interface RunSummary {
	readonly id: string;
	readonly project_id: string;
	readonly revision: number;
	readonly manifest_sha256: string;
	readonly result_sha256: string | null;
	readonly state: RunState;
	readonly is_current: boolean;
	readonly created_at: number;
	readonly task_kind?: string | null;
}
export interface PlanningRun extends Omit<RunSummary, "created_at"> {
	readonly manifest: JsonObject;
	readonly result: JsonObject | null;
	readonly error: JsonObject | null;
}
export interface RunPage {
	readonly items: readonly RunSummary[];
	readonly next: {
		readonly before_created_at: number;
		readonly before_id: string;
	} | null;
}
export interface BatteryAsset extends JsonObject {
	readonly id: string;
	readonly project_id: string;
	readonly content_sha256: string;
	readonly metadata_sha256: string;
	readonly media_type: "application/json";
	readonly purpose: "battery_parameters_v1";
	readonly metadata: JsonObject;
}
const hash = (value: unknown, length = 64): value is string =>
	typeof value === "string" && new RegExp(`^[a-f0-9]{${length}}$`).test(value);
const revision = (value: unknown): value is number =>
	typeof value === "number" && Number.isSafeInteger(value) && value > 0;
const exact = (value: JsonObject, keys: readonly string[]) =>
	Object.keys(value).sort().join() === [...keys].sort().join();

export function readPlanningOperation(
	path: PlanningOperation,
	body: string,
): JsonObject {
	const command = readObject(JSON.parse(body));
	if (
		!isPlanningOperation(path) ||
		command.schema_version !== 1 ||
		!hash(command.project_id, 32) ||
		typeof command.key !== "string" ||
		!/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(
			command.key,
		)
	)
		throw new ApiError(422, "invalid_energy_intent");
	if (path !== "battery/scenario") {
		if (
			!exact(command, [
				"schema_version",
				"project_id",
				"expected_revision",
				"key",
				...(path === "runs/report" ? ["options"] : []),
				...(path === "draft/apply"
					? ["report_run_id", "expected_draft_sha256"]
					: []),
			]) ||
			!revision(command.expected_revision)
		)
			throw new ApiError(422, "invalid_energy_intent");
		if (path === "runs/report") readReportOptions(command.options);
		if (
			path === "draft/apply" &&
			(!hash(command.report_run_id, 32) ||
				!hash(command.expected_draft_sha256, 64))
		)
			throw new ApiError(422, "invalid_energy_intent");
	} else {
		const dc = readObject(command.parameters).model === DC_MODEL;
		if (
			!exact(command, [
				"schema_version",
				"project_id",
				"source_note",
				"parameters",
				"key",
				...(dc ? ["expected_revision"] : []),
			]) ||
			typeof command.source_note !== "string" ||
			!command.source_note.trim()
		)
			throw new ApiError(422, "invalid_energy_intent");
		if (dc) {
			if (!revision(command.expected_revision))
				throw new ApiError(422, "invalid_energy_intent");
			readDcLossScenario(command.parameters);
		} else readBatteryParameters(command.parameters);
	}
	return command;
}

function readBatteryAssetDocument(
	value: unknown,
	projectId: string,
	sourceNote: string,
): BatteryAsset {
	const row = readObject(value),
		metadata = readObject(row.metadata),
		provenance = readObject(metadata.provenance);
	if (
		!exact(row, [
			"id",
			"project_id",
			"content_sha256",
			"metadata_sha256",
			"media_type",
			"purpose",
			"metadata",
		]) ||
		!hash(row.id, 32) ||
		row.project_id !== projectId ||
		!hash(row.content_sha256) ||
		!hash(row.metadata_sha256) ||
		row.purpose !== "battery_parameters_v1" ||
		row.media_type !== "application/json" ||
		metadata.retention !== "permanent" ||
		provenance.basis !== "user_explicit_scenario_not_equipment_release" ||
		provenance.label !== sourceNote
	)
		throw new ApiError(502, "invalid_battery_reply");
	return row as BatteryAsset;
}

function runIdentity(row: JsonObject, projectId: string) {
	if (
		!hash(row.id, 32) ||
		row.project_id !== projectId ||
		!revision(row.revision) ||
		!hash(row.manifest_sha256) ||
		(row.result_sha256 !== null && !hash(row.result_sha256)) ||
		typeof row.state !== "string" ||
		!(RUN_STATES as readonly string[]).includes(row.state) ||
		typeof row.is_current !== "boolean"
	)
		throw new ApiError(502, "invalid_run_reply");
}
function readRunDocument(
	value: unknown,
	projectId: string,
	expectedId?: string,
	expectedTask?: TaskKind,
): PlanningRun {
	const row = readObject(value);
	runIdentity(row, projectId);
	if (
		!exact(row, [
			"id",
			"project_id",
			"revision",
			"manifest_sha256",
			"result_sha256",
			"state",
			"is_current",
			"manifest",
			"result",
			"error",
		]) ||
		(expectedId !== undefined && row.id !== expectedId)
	)
		throw new ApiError(502, "invalid_run_reply");
	const manifest = readObject(row.manifest),
		context = readObject(manifest.context);
	if (
		manifest.schema !== 1 ||
		manifest.project_id !== projectId ||
		manifest.revision !== row.revision ||
		!hash(manifest.input_sha256) ||
		!hash(context.code_sha256)
	)
		throw new ApiError(502, "invalid_run_reply");
	const models = readObject(context.models);
	readObject(context.assets);
	readObject(context.parameters);
	const task = runTask({ manifest });
	if (
		(expectedTask !== undefined &&
			task !== expectedTask &&
			!(
				expectedTask === RUN_OPERATIONS["runs/energy"] && isEnergyTask(task)
			)) ||
		(isEnergyTask(task) && models.replay !== task) ||
		((task === RUN_OPERATIONS["runs/equipment"] ||
			task === SEARCH_TASK ||
			task === REPORT_TASK ||
			task === RUN_OPERATIONS["runs/pv"] ||
			task === RUN_OPERATIONS["runs/weather"]) &&
			models.task !== task)
	)
		throw new ApiError(502, "invalid_run_reply");
	if (row.error !== null) readObject(row.error);
	if (row.result !== null) {
		if (
			task === RUN_OPERATIONS["runs/pv"] ||
			task === RUN_OPERATIONS["runs/weather"]
		)
			readPreparationResult(row.result, row, manifest, task);
		else if (isEnergyTask(task)) readEnergyResult(row.result, row, manifest);
		else if (task === SEARCH_TASK)
			readEquipmentSearchResult(row.result, row, manifest);
		else if (task === REPORT_TASK) readReportResult(row.result, row, manifest);
		else if (task === EQUIPMENT_TASK)
			readEquipmentResult(row.result, row, manifest);
		else throw new ApiError(502, "unsupported_run_model");
	} else if (row.state === "succeeded" || row.result_sha256 !== null)
		throw new ApiError(502, "invalid_run_result");
	return row as unknown as PlanningRun;
}

function readRunPageDocument(value: unknown, projectId: string): RunPage {
	const row = readObject(value);
	if (!exact(row, ["items", "next"]) || !Array.isArray(row.items))
		throw new ApiError(502, "invalid_run_page");
	for (const item of row.items) {
		const summary = readObject(item);
		runIdentity(summary, projectId);
		if (
			!exact(summary, [
				"id",
				"project_id",
				"revision",
				"manifest_sha256",
				"result_sha256",
				"state",
				"is_current",
				"created_at",
				...(Object.hasOwn(summary, "task_kind") ? ["task_kind"] : []),
			]) ||
			(summary.task_kind !== undefined &&
				summary.task_kind !== null &&
				(typeof summary.task_kind !== "string" ||
					!summary.task_kind.trim() ||
					summary.task_kind.length > 128)) ||
			typeof summary.created_at !== "number" ||
			!Number.isFinite(summary.created_at) ||
			!Number.isFinite(new Date(summary.created_at * 1000).getTime()) ||
			summary.created_at < 0
		)
			throw new ApiError(502, "invalid_run_page");
	}
	if (row.next !== null) {
		const next = readObject(row.next);
		if (
			!exact(next, ["before_created_at", "before_id"]) ||
			!hash(next.before_id, 32) ||
			typeof next.before_created_at !== "number" ||
			!Number.isFinite(next.before_created_at) ||
			next.before_created_at < 0
		)
			throw new ApiError(502, "invalid_run_page");
	}
	return row as unknown as RunPage;
}

export function runPending(state: RunState): boolean {
	return state === "queued" || state === "running" || state === "retry_wait";
}

export function readRun(
	value: unknown,
	projectId: string,
	expectedId?: string,
	expectedTask?: TaskKind,
): PlanningRun {
	try {
		return readRunDocument(value, projectId, expectedId, expectedTask);
	} catch (error) {
		if (error instanceof ApiError && error.status === 502) throw error;
		throw new ApiError(502, "invalid_run_reply");
	}
}

export function readRunPage(value: unknown, projectId: string): RunPage {
	try {
		return readRunPageDocument(value, projectId);
	} catch (error) {
		if (error instanceof ApiError && error.status === 502) throw error;
		throw new ApiError(502, "invalid_run_page");
	}
}

export function readBatteryAsset(
	value: unknown,
	projectId: string,
	sourceNote: string,
	command?: JsonObject,
): BatteryAsset {
	try {
		const asset = readBatteryAssetDocument(value, projectId, sourceNote);
		if (command && readObject(command.parameters).model === DC_MODEL) {
			const dependencies = readObject(asset.metadata.dependencies);
			if (
				asset.metadata.derived_from_revision !== command.expected_revision ||
				Object.keys(dependencies).sort().join() !==
					"dc_prepared_parameters,dc_woo_inputs" ||
				!Object.values(dependencies).every((v) => hash(v))
			)
				throw new ApiError(502, "invalid_battery_reply");
		}
		return asset;
	} catch (error) {
		if (error instanceof ApiError && error.status === 502) throw error;
		throw new ApiError(502, "invalid_battery_reply");
	}
}
