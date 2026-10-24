import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import { RUN_STATES, runPending } from "./planningProtocol.ts";
import type { RunState } from "./planningProtocol.ts";

const ACQUISITION_STATES = [
	"not_started",
	"ready_to_start",
	"start_outcome_unknown",
	"captured",
	"READY",
	"RUNNING",
	"TIMING-OUT",
	"ABORTING",
	"SUCCEEDED",
	"FAILED",
	"TIMED-OUT",
	"ABORTED",
] as const;
export type AcquisitionState = (typeof ACQUISITION_STATES)[number];
export interface WeatherStatus {
	readonly runId: string;
	readonly taskState: RunState;
	readonly acquisitionState: AcquisitionState;
	readonly cleanup: RunState | null;
	readonly reconciliation: RunState | null;
}
const state = (v: unknown): v is RunState =>
	(RUN_STATES as readonly unknown[]).includes(v);
const hash = (v: unknown): v is string =>
	typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
function maintenance(value: unknown): RunState | null {
	if (value === null || value === undefined) return null;
	const row = readObject(value);
	if (
		!state(row.state) ||
		!Number.isSafeInteger(row.attempt) ||
		Number(row.attempt) < 0 ||
		!Number.isSafeInteger(row.max_attempts) ||
		Number(row.max_attempts) < 1 ||
		Number(row.attempt) > Number(row.max_attempts)
	)
		throw new ApiError(502, "invalid_weather_status");
	return row.state;
}
export function readWeatherStatus(
	value: unknown,
	runId: string,
): WeatherStatus {
	try {
		const row = readObject(value);
		if (
			row.schema_version !== 1 ||
			row.run_id !== runId ||
			!/^[a-f0-9]{32}$/.test(runId) ||
			!state(row.task_state) ||
			!(ACQUISITION_STATES as readonly unknown[]).includes(
				row.acquisition_state,
			)
		)
			throw new Error("invalid status");
		if (row.acquisition_state !== "not_started") {
			if (
				!hash(row.plan_sha256) ||
				(row.capture_sha256 !== null && !hash(row.capture_sha256)) ||
				(row.abort_sha256 !== null && !hash(row.abort_sha256))
			)
				throw new Error("invalid evidence");
			if (row.observation !== null) {
				const observed = readObject(row.observation);
				if (
					row.acquisition_state !== "captured" &&
					observed.status !== row.acquisition_state
				)
					throw new Error("different observation");
				if (
					row.acquisition_state === "captured" &&
					(observed.status !== "SUCCEEDED" || !hash(row.capture_sha256))
				)
					throw new Error("invalid capture");
			} else if (
				!["ready_to_start", "start_outcome_unknown"].includes(
					String(row.acquisition_state),
				)
			)
				throw new Error("missing observation");
		}
		return {
			runId,
			taskState: row.task_state,
			acquisitionState: row.acquisition_state as AcquisitionState,
			cleanup: maintenance(row.cleanup),
			reconciliation: maintenance(row.reconciliation),
		};
	} catch {
		throw new ApiError(502, "invalid_weather_status");
	}
}
export function weatherStatusPending(status: WeatherStatus): boolean {
	return (
		runPending(status.taskState) ||
		(status.cleanup !== null && runPending(status.cleanup)) ||
		(status.reconciliation !== null && runPending(status.reconciliation))
	);
}
