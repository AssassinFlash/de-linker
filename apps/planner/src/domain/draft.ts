import { change, newHistory, redo, undo } from "./history.ts";
import type { History } from "./history.ts";
import type { JsonObject, Project } from "../data/protocol.ts";
import { wire } from "../data/readProtocol.ts";

/** A save intent is immutable, even when further local edits are made. */
export interface SaveIntent {
	readonly key: string;
	readonly projectId: string;
	readonly expectedRevision: number;
	readonly inputs: JsonObject;
	readonly body: string;
}
export interface Draft {
	readonly baseline: Project;
	readonly history: History<JsonObject>;
	readonly pending: SaveIntent | null;
	readonly conflict: Project | null;
}

// Editing resource policy: retain 100 snapshots, independently of physical scope.
const HISTORY_ENTRIES = 100;
export function beginDraft(project: Project): Draft {
	return {
		baseline: project,
		history: newHistory(project.inputs),
		pending: null,
		conflict: null,
	};
}
export function editDraft(draft: Draft, inputs: JsonObject): Draft {
	return sameJson(draft.history.current, inputs)
		? draft
		: { ...draft, history: change(draft.history, inputs, HISTORY_ENTRIES) };
}
export function undoDraft(draft: Draft): Draft {
	return { ...draft, history: undo(draft.history) };
}
export function redoDraft(draft: Draft): Draft {
	return { ...draft, history: redo(draft.history) };
}
export function isDirty(draft: Draft): boolean {
	return !sameJson(draft.baseline.inputs, draft.history.current);
}

/** Captured once; retransmission must not regenerate key, revision or snapshot. */
export function prepareSave(
	draft: Draft,
	key: string,
	policy: { maxDepth: number; maxBytes: number },
): Draft {
	if (draft.pending || draft.conflict || !isDirty(draft)) return draft;
	if (
		!/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(
			key,
		)
	)
		throw new Error("invalid_save_key");
	const inputs = structuredClone(draft.history.current);
	const pending: SaveIntent = {
		key,
		projectId: draft.baseline.id,
		expectedRevision: draft.baseline.revision,
		inputs,
		body: wire(
			{
				schema_version: 1,
				project_id: draft.baseline.id,
				expected_revision: draft.baseline.revision,
				inputs,
				key,
			},
			policy.maxDepth,
			policy.maxBytes,
		),
	};
	return { ...draft, pending };
}

export function acknowledgeSave(
	draft: Draft,
	intent: SaveIntent,
	project: Project,
): Draft {
	if (draft.pending?.key !== intent.key)
		throw new Error("save_acknowledgement_mismatch");
	if (
		project.id !== intent.projectId ||
		project.revision !== intent.expectedRevision + 1 ||
		!sameJson(project.inputs, intent.inputs)
	)
		throw new Error("invalid_save_acknowledgement");
	// A reply for an older snapshot advances the baseline, preserving later edits
	// and their undo history. It never labels a newer local document as saved.
	return { ...draft, baseline: project, pending: null, conflict: null };
}

export function markConflict(draft: Draft, remote: Project): Draft {
	if (
		remote.id !== draft.baseline.id ||
		remote.revision < draft.baseline.revision
	)
		throw new Error("invalid_conflict_revision");
	return { ...draft, conflict: remote };
}
export function keepLocalAgainst(draft: Draft): Draft {
	if (!draft.conflict) return draft;
	return { ...draft, baseline: draft.conflict, pending: null, conflict: null };
}
export function useRemote(draft: Draft): Draft {
	return draft.conflict ? beginDraft(draft.conflict) : draft;
}

/** Structural equality only; the server alone owns canonical command hashes. */
export function sameJson(left: unknown, right: unknown): boolean {
	// JSON serialises both signed zeroes as 0. Exact structural equality must
	// agree with the wire, including trig-derived -0 geometry coordinates.
	if (left === right) return true;
	if (
		left === null ||
		right === null ||
		typeof left !== "object" ||
		typeof right !== "object"
	)
		return false;
	if (Array.isArray(left) || Array.isArray(right))
		return (
			Array.isArray(left) &&
			Array.isArray(right) &&
			left.length === right.length &&
			left.every((value: unknown, index: number) =>
				sameJson(value, right[index]),
			)
		);
	const a = left as Record<string, unknown>;
	const b = right as Record<string, unknown>;
	const keys = Object.keys(a);
	return (
		keys.length === Object.keys(b).length &&
		keys.every((key) => Object.hasOwn(b, key) && sameJson(a[key], b[key]))
	);
}
