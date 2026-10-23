import Ajv from "ajv";
import { inspectJson } from "./inspectJson.ts";

export interface LayoutIssue {
	kind: string;
	object_id: string;
	roof_id: string | null;
	related_id: string | null;
	category: "missing_input" | "layout_conflict" | "numerical_limit";
	required_m: number | null;
	actual_m: number | null;
}
export interface LayoutReview {
	schema_version: 1;
	geometry_sha256: string;
	runtime_sha256: string;
	checker: string;
	uv_resolution_m: number;
	libraries: { shapely: string; geos: string };
	geometry_status:
		"incomplete" | "conflicts_detected" | "no_conflicts_detected";
	engineering_status: "not_evaluated";
	review_complete: boolean;
	diagnostics_truncated: boolean;
	issue_count: number;
	conflict_count: number;
	candidate_checks: number;
	module_count: number;
	declared_stc_kwp: number;
	limits: {
		max_diagnostics: number;
		max_candidate_checks: number;
		max_uv_resolution_m: number;
	};
	issues: readonly LayoutIssue[];
}
const object = (properties: Record<string, object>) => ({
	type: "object",
	required: Object.keys(properties),
	additionalProperties: false,
	properties,
});
const string = { type: "string", minLength: 1, maxLength: 4096 };
const nonnegative = { type: "number", minimum: 0 };
const integer = {
	type: "integer",
	minimum: 0,
	maximum: Number.MAX_SAFE_INTEGER,
};
const hash = { type: "string", pattern: "^[a-f0-9]{64}$" };
const nullable = (value: object) => ({ anyOf: [value, { type: "null" }] });
const check = new Ajv({
	strict: true,
	strictNumbers: true,
}).compile<LayoutReview>(
	object({
		schema_version: { const: 1, type: "integer" },
		geometry_sha256: hash,
		runtime_sha256: hash,
		checker: string,
		uv_resolution_m: nonnegative,
		libraries: object({ shapely: string, geos: string }),
		geometry_status: {
			enum: ["incomplete", "conflicts_detected", "no_conflicts_detected"],
		},
		engineering_status: { const: "not_evaluated", type: "string" },
		review_complete: { type: "boolean" },
		diagnostics_truncated: { type: "boolean" },
		issue_count: integer,
		conflict_count: integer,
		candidate_checks: integer,
		module_count: integer,
		declared_stc_kwp: nonnegative,
		limits: object({
			max_diagnostics: integer,
			max_candidate_checks: integer,
			max_uv_resolution_m: nonnegative,
		}),
		issues: {
			type: "array",
			maxItems: 200,
			items: object({
				kind: string,
				object_id: string,
				roof_id: nullable(string),
				related_id: nullable(string),
				category: {
					enum: ["missing_input", "layout_conflict", "numerical_limit"],
				},
				required_m: nullable(nonnegative),
				actual_m: nullable(nonnegative),
			}),
		},
	}),
);
export function readLayoutReview(value: unknown): LayoutReview {
	inspectJson(value, 16);
	if (
		!check(value) ||
		value.issues.length > value.issue_count ||
		value.conflict_count > value.issue_count ||
		value.review_complete === (value.geometry_status === "incomplete")
	)
		throw new Error("invalid_geometry_review");
	return value;
}
