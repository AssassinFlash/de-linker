import type { ProfileIssue } from "./profileIssue.ts";
/** Native gateway views; no owner secret or browser-selected principal. */
export type Json =
	null | boolean | number | string | readonly Json[] | JsonObject;
export interface JsonObject {
	readonly [key: string]: Json;
}

export interface Project {
	readonly id: string;
	readonly title: string;
	readonly revision: number;
	readonly input_sha256: string;
	readonly inputs: JsonObject;
}

export interface Session {
	readonly schema_version: 1;
	readonly kind: "guest" | "user";
	readonly cookie_confirmed: boolean;
	readonly expires_at: number;
	readonly query_scope: string;
	readonly nonce: string;
	readonly claim_pending: boolean;
	readonly runtime: {
		readonly schema_version: 1;
		readonly runtime_sha256: string;
		readonly models: Readonly<Record<string, string>>;
		readonly limits: {
			readonly max_body_bytes: number;
			readonly max_csv_bytes: number;
			readonly max_page_size: number;
			readonly max_json_depth: number;
			readonly direct_beam_visibility?: {
				readonly max_selected_rows: number;
				readonly max_samples: number;
				readonly max_ray_face_checks: number;
				readonly max_bounds_checks: number;
				readonly index_leaf_size: number;
			};
			readonly geometric_pv_generation?: {
				readonly max_module_steps: number;
				readonly max_samples: number;
				readonly max_ray_face_checks: number;
				readonly max_bounds_checks: number;
				readonly index_leaf_size: number;
			};
			readonly geometric_pv_clear_flat_roof?: {
				readonly max_module_steps: number;
				readonly max_samples: number;
				readonly max_modules: number;
				readonly max_strings: number;
				readonly max_weather_rows: number;
			};
			readonly geometric_pv_clear_pitched_roof?: {
				readonly max_module_steps: number;
				readonly max_samples: number;
				readonly max_modules: number;
				readonly max_strings: number;
				readonly max_weather_rows: number;
			};
		};
	};
}

export const RPC_PATHS = [
	"inquiry/form",
	"draft/preview",
	"draft/apply",
	"draft/read",
	"products/current",
	"products/cards",
	"sources/saved-solution",
	"sources/project-brief",
	"sources/project-brief/stage",
	"projects/create",
	"projects/delete",
	"projects/list",
	"projects/read",
	"projects/revise",
	"projects/runs",
	"runs/read",
	"runs/inputs",
	"runs/compare",
	"runs/cancel",
	"runs/energy",
	"runs/calculate",
	"runs/find-equipment",
	"runs/check-equipment",
	"runs/pv",
	"runs/pvgis-reference",
	"runs/direct-beam",
	"runs/geometric-pv",
	"weather/assets",
	"weather/preview",
	"runs/equipment",
	"runs/equipment-search",
	"runs/report",
	"design/commercial",
	"places/lookup",
	"places/outline",
	"equipment/candidates/read",
	"equipment/certificates/read",
	"runs/weather",
	"runs/weather/status",
	"runs/trace",
	"assets/read",
	"assets/content",
	"profiles/csv",
	"profiles/standard",
	"profiles/inspect",
	"profiles/preview",
	"geometry/review",
	"installation/review",
	"geometry/import",
	"battery/scenario",
	"recovery/scopes",
] as const;
export type RpcPath = (typeof RPC_PATHS)[number];
export type JsonRpcPath = Exclude<RpcPath, "assets/content">;

export class ApiError extends Error {
	readonly status: number;
	readonly code: string;
	readonly profileIssue: ProfileIssue | null;
	readonly evidenceIssue: EvidenceIssue | null;
	readonly fields: readonly string[];

	constructor(
		status: number,
		code: string,
		profileIssue: ProfileIssue | null = null,
		evidenceIssue: EvidenceIssue | null = null,
		fields: readonly string[] = [],
	) {
		super(code);
		this.name = "ApiError";
		this.status = status;
		this.code = code;
		this.profileIssue = profileIssue;
		this.evidenceIssue = evidenceIssue;
		this.fields = fields;
	}
}

/** Match the HTTP validation handler's 16 paths and 16 bounded path segments.
 * Only schema identifiers survive; submitted values and messages are discarded. */
export function readInputFields(value: unknown): readonly string[] {
	if (!Array.isArray(value)) return [];
	const fields: string[] = [];
	for (const item of value.slice(0, 16)) {
		let path: string;
		if (typeof item === "string") path = item;
		else if (
			item &&
			typeof item === "object" &&
			Array.isArray(item.path) &&
			item.path.length <= 16 &&
			item.path.every(
				(part: unknown) =>
					(typeof part === "string" &&
						part.length <= 64 &&
						/^(?:[A-Za-z_][A-Za-z0-9_]*|[0-9]+)$/.test(part)) ||
					(typeof part === "number" && Number.isSafeInteger(part) && part >= 0),
			)
		)
			path = item.path
				.map((part: string | number, index: number) =>
					/^\d+$/.test(String(part)) ? `[${part}]` : (index ? "." : "") + part,
				)
				.join("");
		else continue;
		path = path.replace(/^body\./, "").replace(/^inputs\./, "");
		if (
			path.length <= 1040 &&
			/^[A-Za-z_][A-Za-z0-9_]*(?:(?:\.[A-Za-z_][A-Za-z0-9_]*)|(?:\[[0-9]+\]))*$/.test(
				path,
			)
		)
			fields.push(path);
	}
	return [...new Set(fields)];
}

export function clearInputFields(
	error: unknown,
	changed?: readonly string[],
): unknown {
	if (!changed || !(error instanceof ApiError) || !error.fields.length)
		return null;
	const remaining = error.fields.filter(
		(field) =>
			!changed.some(
				(path) =>
					field === path ||
					field.startsWith(path + ".") ||
					field.startsWith(path + "["),
			),
	);
	if (remaining.length === error.fields.length) return error;
	return remaining.length
		? new ApiError(
				error.status,
				error.code,
				error.profileIssue,
				error.evidenceIssue,
				remaining,
			)
		: null;
}

export interface EvidenceIssue {
	readonly product_id?: number;
	readonly fact_id?: string;
	readonly constraint_id?: string;
}
/** Only canonical source identifiers may leave the service; diagnostics stay private. */
export function readEvidenceIssue(value: unknown): EvidenceIssue | null {
	if (!value || typeof value !== "object" || Array.isArray(value)) return null;
	const row = value as Record<string, unknown>;
	if (
		Object.keys(row).some(
			(key) => !["product_id", "fact_id", "constraint_id"].includes(key),
		) ||
		!Object.keys(row).length
	)
		return null;
	if (
		row.product_id !== undefined &&
		(typeof row.product_id !== "number" ||
			!Number.isSafeInteger(row.product_id) ||
			row.product_id <= 0)
	)
		return null;
	for (const key of ["fact_id", "constraint_id"])
		if (
			row[key] !== undefined &&
			(typeof row[key] !== "string" || !/^[a-z][a-z0-9_.:-]*$/.test(row[key]))
		)
			return null;
	return row as EvidenceIssue;
}
