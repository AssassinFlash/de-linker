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
		};
	};
}

export const RPC_PATHS = [
	"draft/preview",
	"draft/apply",
	"draft/read",
	"products/current",
	"projects/create",
	"projects/list",
	"projects/read",
	"projects/revise",
	"projects/runs",
	"runs/read",
	"runs/compare",
	"runs/cancel",
	"runs/energy",
	"runs/pv",
	"runs/equipment",
	"runs/equipment-search",
	"runs/report",
	"equipment/candidates/read",
	"runs/weather",
	"runs/weather/status",
	"runs/trace",
	"assets/read",
	"assets/content",
	"profiles/csv",
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

	constructor(
		status: number,
		code: string,
		profileIssue: ProfileIssue | null = null,
		evidenceIssue: EvidenceIssue | null = null,
	) {
		super(code);
		this.name = "ApiError";
		this.status = status;
		this.code = code;
		this.profileIssue = profileIssue;
		this.evidenceIssue = evidenceIssue;
	}
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
