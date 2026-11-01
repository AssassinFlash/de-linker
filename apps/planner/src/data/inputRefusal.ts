import { ApiError } from "./protocol.ts";

/** Only an identified noncommit releases a frozen request.
 * Native planning draft errors include an explicitly confirmed rollback.
 * A proxy's status alone cannot establish whether the server committed.
 * Codes come from PlannerClient/readProtocol, the native Planner BodyGate and
 * the engine's http_app/service_boundary input handlers. */
export function isPreMutationInputRefusal(error: unknown): boolean {
	if (!(error instanceof ApiError)) return false;
	const statuses: Readonly<Record<string, readonly number[]>> = {
		invalid_input: [400, 422],
		project_input_contract_required: [422],
		handoff_incomplete: [422],
		handoff_revision_changed: [409],
		planning_draft_changed: [409],
		linker_solution_changed: [409],
		report_inputs_changed: [422],
		report_source_export_required: [422],
		geometric_pv_expanded_scope_required: [422],
		report_logo_invalid: [422],
		product_evidence_changed: [409],
		body_too_large: [413],
		request_too_large: [413],
		linker_planner_body: [413],
		linker_planner_content_type: [415],
		linker_planner_input: [400],
		linker_planner_input_depth: [400],
	};
	// Shared JSON/shape validators also run after dispatch on response bytes.
	// Their codes (including invalid_json_object) cannot prove a refused write.
	return Object.hasOwn(statuses, error.code)
		? statuses[error.code]!.includes(error.status)
		: false;
}
