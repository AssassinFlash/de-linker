import assert from "node:assert/strict";
import { test } from "node:test";
import {
	acknowledgeSave,
	beginDraft,
	editDraft,
	isDirty,
	keepLocalAgainst,
	markConflict,
	prepareSave,
	redoDraft,
	undoDraft,
	useRemote,
} from "./draft.ts";
import type { Project } from "../data/protocol.ts";

const project: Project = {
	id: "a".repeat(32),
	title: "Site",
	revision: 1,
	input_sha256: "b".repeat(64),
	inputs: { site: { country_code: "DE" }, value: 1 },
};
const key = "37c3a9ef-4d58-49df-b38e-61090c8a19aa";
const policy = { maxDepth: 32, maxBytes: 16777216 };

test("a late acknowledgement preserves newer edits and their undo/redo history", () => {
	let draft = editDraft(beginDraft(project), { ...project.inputs, value: 2 });
	draft = prepareSave(draft, key, policy);
	const intent = draft.pending;
	assert.ok(intent);
	const wire = intent.body;
	assert.equal(
		JSON.parse(wire).input_contract,
		"pv_string_links_direct_beam_geometric_pv_v1",
	);
	draft = editDraft(draft, { ...project.inputs, value: 3 });
	assert.equal(prepareSave(draft, crypto.randomUUID(), policy).pending, intent);
	assert.equal(intent.body, wire);
	draft = acknowledgeSave(draft, intent, {
		...project,
		revision: 2,
		inputs: intent.inputs,
	});
	assert.equal(draft.baseline.revision, 2);
	assert.equal(draft.history.current.value, 3);
	assert.equal(isDirty(draft), true);
	draft = undoDraft(draft);
	assert.equal(draft.history.current.value, 2);
	assert.equal(isDirty(draft), false);
	assert.equal(redoDraft(draft).history.current.value, 3);
});

test("conflict resolution is explicit and preserves the local branch until chosen", () => {
	const remote = {
		...project,
		revision: 2,
		inputs: { ...project.inputs, value: 4 },
	};
	const local = editDraft(beginDraft(project), { ...project.inputs, value: 3 });
	const conflicted = markConflict(prepareSave(local, key, policy), remote);
	assert.equal(conflicted.history.current.value, 3);
	assert.equal(
		prepareSave(conflicted, crypto.randomUUID(), policy),
		conflicted,
	);
	const chosen = keepLocalAgainst(conflicted);
	assert.equal(chosen.baseline, remote);
	assert.equal(chosen.history.current.value, 3);
	assert.equal(
		prepareSave(chosen, crypto.randomUUID(), policy).pending?.expectedRevision,
		2,
	);
	assert.equal(useRemote(conflicted).history.current.value, 4);
});

test("incorrect save acknowledgements cannot advance the confirmed baseline", () => {
	const draft = prepareSave(
		editDraft(beginDraft(project), { value: 2 }),
		key,
		policy,
	);
	const intent = draft.pending;
	assert.ok(intent);
	assert.throws(
		() =>
			acknowledgeSave(draft, intent, {
				...project,
				revision: 2,
				inputs: { value: 3 },
			}),
		/invalid_save_acknowledgement/,
	);
	assert.throws(
		() => acknowledgeSave(draft, { ...intent, key: "other" }, project),
		/save_acknowledgement_mismatch/,
	);
	assert.equal(draft.baseline, project);
});

test("wire-equivalent signed zeroes acknowledge saved geometry without rewriting the local input", () => {
	const draft = editDraft(beginDraft(project), { axis: [-1, -0, 0] });
	const prepared = prepareSave(draft, key, policy),
		intent = prepared.pending!;
	const reply = {
		...project,
		revision: 2,
		inputs: JSON.parse(intent.body).inputs,
	};
	const acknowledged = acknowledgeSave(prepared, intent, reply);
	assert.equal(acknowledged.pending, null);
	assert.equal(isDirty(acknowledged), false);
	assert.ok(
		Object.is((acknowledged.history.current.axis as readonly number[])[1], -0),
	);
	assert.ok(Object.is((reply.inputs.axis as readonly number[])[1], 0));
});
