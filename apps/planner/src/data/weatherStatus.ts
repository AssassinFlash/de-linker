import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import { RUN_STATES, runPending } from "./planningProtocol.ts";
import type { RunState } from "./planningProtocol.ts";

const ACQUISITION_STATES = [
	"not_started",
	"fetching",
	"captured",
	"rejected",
] as const;
export type AcquisitionState = (typeof ACQUISITION_STATES)[number];
export interface WeatherQualityFailure {
	readonly code: "weather_source_quality_invalid";
	readonly reason: "negative_wind" | "negative_irradiance";
	readonly field: "WS10m" | "G(h)" | "Gb(n)" | "Gd(h)";
	readonly rowIndex: number;
	readonly sourceTimestampUtc: string;
	readonly value: number;
}
export type WeatherValidationFailure =
	| WeatherQualityFailure
	| {
			readonly code: "weather_response_invalid";
			readonly reason: "response_validation_failed";
	  };
export interface WeatherStatus {
	readonly runId: string;
	readonly taskState: RunState;
	readonly acquisitionState: AcquisitionState;
	readonly validationFailure?: WeatherValidationFailure;
}
const hash = (v: unknown): v is string =>
	typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
function readValidationFailure(value: unknown): WeatherValidationFailure {
	const row = readObject(value);
	if (
		row.code === "weather_response_invalid" &&
		row.reason === "response_validation_failed"
	)
		return { code: row.code, reason: row.reason };
	if (
		row.code !== "weather_source_quality_invalid" ||
		!(
			(row.reason === "negative_wind" && row.field === "WS10m") ||
			(row.reason === "negative_irradiance" &&
				["G(h)", "Gb(n)", "Gd(h)"].includes(String(row.field)))
		) ||
		typeof row.row_index !== "number" ||
		!Number.isSafeInteger(row.row_index) ||
		row.row_index < 0 ||
		typeof row.source_timestamp_utc !== "string" ||
		!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)$/.test(
			row.source_timestamp_utc,
		) ||
		!Number.isFinite(Date.parse(row.source_timestamp_utc)) ||
		typeof row.value !== "number" ||
		!Number.isFinite(row.value) ||
		row.value >= 0
	)
		throw new Error("invalid weather validation failure");
	return {
		code: row.code,
		reason: row.reason,
		field: row.field as WeatherQualityFailure["field"],
		rowIndex: row.row_index,
		sourceTimestampUtc: row.source_timestamp_utc,
		value: row.value,
	};
}
/** Only enumerated failure fields can reach customer presentation. */
export function weatherFailureFromRun(
	value: unknown,
): WeatherValidationFailure | null {
	try {
		const row = readObject(value);
		if (row.retryable !== false) return null;
		if (row.code === "weather_response_invalid")
			return { code: row.code, reason: "response_validation_failed" };
		if (row.code !== "weather_source_quality_invalid") return null;
		return readValidationFailure({
			...readObject(row.details),
			code: row.code,
		});
	} catch {
		return null;
	}
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
		let validationFailure: WeatherValidationFailure | undefined;
		if (row.acquisition_state === "rejected") {
			if (
				row.task_state !== "failed" ||
				row.capture_sha256 !== null ||
				row.diagnostic_retained !== true
			)
				throw new Error("invalid rejected source");
			validationFailure = readValidationFailure(row.validation_failure);
		} else if (
			row.validation_failure !== undefined ||
			row.diagnostic_retained !== undefined
		)
			throw new Error("invalid source diagnostic state");
		return {
			runId,
			taskState: row.task_state as RunState,
			acquisitionState: row.acquisition_state as AcquisitionState,
			...(validationFailure === undefined ? {} : { validationFailure }),
		};
	} catch {
		throw new ApiError(502, "invalid_weather_status");
	}
}
export function weatherStatusPending(status: WeatherStatus): boolean {
	return runPending(status.taskState);
}
