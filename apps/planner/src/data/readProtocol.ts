import Ajv from "ajv";
import { ApiError } from "./protocol.ts";
import { inspectJson } from "./inspectJson.ts";
import type { JsonObject, Project, Session } from "./protocol.ts";

const hex = (length: number): object => ({
	type: "string",
	pattern: `^[a-f0-9]{${length}}$`,
});
const integer = {
	type: "integer",
	minimum: 1,
	maximum: Number.MAX_SAFE_INTEGER,
};
const object = (properties: Record<string, object>): object => ({
	type: "object",
	properties,
	required: Object.keys(properties),
	additionalProperties: false,
});
const jsonDefinition = {
	anyOf: [
		{ type: "null" },
		{ type: "boolean" },
		{ type: "number" },
		{ type: "string" },
		{ type: "array", items: { $ref: "#/definitions/json" } },
		{ type: "object", additionalProperties: { $ref: "#/definitions/json" } },
	],
};
const definitions = { json: jsonDefinition };
const ajv = new Ajv({ strict: true, strictNumbers: true, allErrors: false });
const checkObject = ajv.compile<JsonObject>({
	definitions,
	type: "object",
	additionalProperties: { $ref: "#/definitions/json" },
});
const checkProject = ajv.compile<Project>({
	definitions,
	...object({
		id: hex(32),
		title: { type: "string", minLength: 1, maxLength: 256 },
		revision: integer,
		input_sha256: hex(64),
		inputs: {
			type: "object",
			additionalProperties: { $ref: "#/definitions/json" },
		},
	}),
});
const checkSession = ajv.compile<Session>(
	object({
		schema_version: { type: "integer", const: 1 },
		kind: { enum: ["guest", "user"] },
		cookie_confirmed: { type: "boolean" },
		expires_at: integer,
		query_scope: hex(64),
		nonce: { type: "string", pattern: "^[a-zA-Z0-9]{10}$" },
		claim_pending: { type: "boolean" },
		runtime: object({
			schema_version: { type: "integer", const: 1 },
			runtime_sha256: hex(64),
			models: {
				type: "object",
				additionalProperties: { type: "string", minLength: 1 },
			},
			limits: {
				...object({
					max_body_bytes: integer,
					max_csv_bytes: integer,
					max_page_size: integer,
					max_json_depth: integer,
					direct_beam_visibility: object({
						max_selected_rows: integer,
						max_samples: integer,
						max_ray_face_checks: integer,
						max_bounds_checks: integer,
						index_leaf_size: integer,
					}),
					geometric_pv_generation: object({
						max_module_steps: integer,
						max_samples: integer,
						max_ray_face_checks: integer,
						max_bounds_checks: integer,
						index_leaf_size: integer,
					}),
				}),
				required: [
					"max_body_bytes",
					"max_csv_bytes",
					"max_page_size",
					"max_json_depth",
				],
			},
		}),
	}),
);

export function readProject(value: unknown): Project {
	inspectJson(value, 40);
	if (!checkProject(value)) throw new ApiError(502, "invalid_project_reply");
	return value;
}
export function readSession(value: unknown): Session {
	inspectJson(value, 16);
	if (!checkSession(value)) throw new ApiError(502, "invalid_session_reply");
	if (value.runtime.limits.max_csv_bytes > value.runtime.limits.max_body_bytes)
		throw new ApiError(502, "invalid_session_reply");
	if (
		(value.runtime.models.direct_beam_visibility ===
			"prepare_direct_beam_visibility_v1") !==
		(value.runtime.limits.direct_beam_visibility !== undefined)
	)
		throw new ApiError(502, "invalid_session_reply");
	if (
		(value.runtime.models.geometric_pv_generation ===
			"prepare_geometric_pv_reference_v1") !==
		(value.runtime.limits.geometric_pv_generation !== undefined)
	)
		throw new ApiError(502, "invalid_session_reply");
	return value;
}
export function readObject(value: unknown, maxDepth = 32): JsonObject {
	inspectJson(value, maxDepth);
	if (!checkObject(value)) throw new ApiError(422, "invalid_json_object");
	return value;
}

/** This is a transport check, not validity of an engineering document. */
export function wire(
	command: JsonObject,
	maxDepth: number,
	maxBytes: number,
): string {
	inspectJson(command, maxDepth);
	readObject(command);
	const body = JSON.stringify(command);
	if (new TextEncoder().encode(body).length > maxBytes)
		throw new ApiError(413, "body_too_large");
	return body;
}
