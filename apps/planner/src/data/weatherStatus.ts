import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import { RUN_STATES, runPending } from "./planningProtocol.ts";
import type { RunState } from "./planningProtocol.ts";

const ACQUISITION_STATES = ["not_started", "fetching", "captured"] as const;
export type AcquisitionState = (typeof ACQUISITION_STATES)[number];
export interface WeatherStatus {
	readonly runId: string;
	readonly taskState: RunState;
	readonly acquisitionState: AcquisitionState;
}
const hash = (v: unknown): v is string =>
	typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
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
			!(RUN_STATES as readonly unknown[]).includes(row.task_state) ||
			!(ACQUISITION_STATES as readonly unknown[]).includes(
				row.acquisition_state,
			)
		)
			throw new Error("invalid status");
		if (
			row.acquisition_state !== "not_started" &&
			(!hash(row.plan_sha256) ||
				(row.capture_sha256 !== null && !hash(row.capture_sha256)))
		)
			throw new Error("invalid download evidence");
		if (
			(row.acquisition_state === "captured" && !hash(row.capture_sha256)) ||
			(row.task_state === "succeeded" && row.acquisition_state !== "captured")
		)
			throw new Error("missing validated original");
		return {
			runId,
			taskState: row.task_state as RunState,
			acquisitionState: row.acquisition_state as AcquisitionState,
		};
	} catch {
		throw new ApiError(502, "invalid_weather_status");
	}
}
export function weatherStatusPending(status: WeatherStatus): boolean {
	return runPending(status.taskState);
}
