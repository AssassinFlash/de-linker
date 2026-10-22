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
	"projects/create",
	"projects/list",
	"projects/read",
	"projects/revise",
	"projects/runs",
	"runs/read",
	"runs/cancel",
	"runs/energy",
	"runs/trace",
	"assets/read",
	"assets/content",
	"profiles/csv",
	"profiles/inspect",
	"profiles/preview",
	"battery/scenario",
] as const;
export type RpcPath = (typeof RPC_PATHS)[number];
export type JsonRpcPath = Exclude<RpcPath, "assets/content">;

export class ApiError extends Error {
	readonly status: number;
	readonly code: string;
	readonly profileIssue: ProfileIssue | null;

	constructor(
		status: number,
		code: string,
		profileIssue: ProfileIssue | null = null,
	) {
		super(code);
		this.name = "ApiError";
		this.status = status;
		this.code = code;
		this.profileIssue = profileIssue;
	}
}
